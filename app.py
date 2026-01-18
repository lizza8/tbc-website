import os
from datetime import datetime
from uuid import uuid4

from dotenv import load_dotenv
from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from flask_login import LoginManager, current_user, login_required, login_user, logout_user
from flask_wtf import CSRFProtect
from werkzeug.utils import secure_filename

from models import Category, Comment, Helpful, Message, Post, User, db

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
ALLOWED_EXTENSIONS = {"pdf", "png", "jpg",
                      "jpeg", "doc", "docx", "ppt", "pptx"}


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-change-me")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'educonnect.db')}"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
    app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    db.init_app(app)
    login_manager = LoginManager()
    login_manager.login_view = "login"
    login_manager.init_app(app)
    CSRFProtect(app)

    with app.app_context():
        db.create_all()
        seed_categories()
        seed_demo_content()

    @login_manager.user_loader
    def load_user(user_id: str):
        return db.session.get(User, int(user_id))

    @app.errorhandler(413)
    def file_too_large(_error):
        flash("ფაილი ძალიან დიდია. მაქსიმუმ 10MB.", "error")
        return redirect(url_for("new_post"))

    @app.errorhandler(404)
    def page_not_found(_error):
        return render_template("404.html"), 404

    @app.route("/")
    def home():
        featured_posts = (
            Post.query.order_by(Post.created_at.desc()).limit(6).all()
        )
        categories = Category.query.order_by(Category.name.asc()).all()
        return render_template(
            "home.html",
            posts=featured_posts,
            categories=categories,
        )

    @app.route("/feed")
    def feed():
        subject = request.args.get("subject", "")
        query = Post.query.order_by(Post.created_at.desc())
        if subject:
            query = query.filter(Post.subject == subject)
        posts = query.all()
        categories = Category.query.order_by(Category.name.asc()).all()
        return render_template(
            "feed.html", posts=posts, categories=categories, subject=subject
        )

    @app.route("/search")
    def search():
        term = request.args.get("q", "").strip()
        posts = []
        if term:
            posts = (
                Post.query.filter(
                    Post.title.ilike(
                        f"%{term}%") | Post.content.ilike(f"%{term}%")
                )
                .order_by(Post.created_at.desc())
                .all()
            )
        return render_template("search.html", term=term, posts=posts)

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if current_user.is_authenticated:
            return redirect(url_for("feed"))
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            email = request.form.get("email", "").strip().lower()
            school = request.form.get("school", "").strip()
            interests = request.form.get("interests", "").strip()
            password = request.form.get("password", "")
            confirm = request.form.get("confirm", "")

            if not name or not email or not school or not password:
                flash("გთხოვ შეავსო ყველა სავალდებულო ველი.", "error")
            elif password != confirm:
                flash("პაროლები არ ემთხვევა.", "error")
            elif User.query.filter_by(email=email).first():
                flash("ეს ელფოსტა უკვე დარეგისტრირებულია.", "error")
            else:
                user = User(
                    name=name,
                    email=email,
                    school=school,
                    interests=interests,
                )
                user.set_password(password)
                db.session.add(user)
                db.session.commit()
                login_user(user)
                return redirect(url_for("feed"))
        return render_template("register.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for("feed"))
        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            user = User.query.filter_by(email=email).first()
            if user and user.check_password(password):
                login_user(user)
                return redirect(url_for("feed"))
            flash("არასწორი ელფოსტა ან პაროლი.", "error")
        return render_template("login.html")

    @app.route("/logout")
    @login_required
    def logout():
        logout_user()
        return redirect(url_for("home"))

    @app.route("/post/new", methods=["GET", "POST"])
    @login_required
    def new_post():
        categories = Category.query.order_by(Category.name.asc()).all()
        if request.method == "POST":
            title = request.form.get("title", "").strip()
            content = request.form.get("content", "").strip()
            subject = request.form.get("subject", "").strip()
            resource_link = request.form.get("resource_link", "").strip()
            resource_file = save_file(request.files.get("resource_file"))

            if not title or not content or not subject:
                flash("სათაური, ტექსტი და თემა სავალდებულოა.", "error")
            else:
                category = Category.query.filter_by(name=subject).first()
                post = Post(
                    title=title,
                    content=content,
                    subject=subject,
                    resource_link=resource_link or None,
                    resource_file=resource_file,
                    author_id=current_user.id,
                    category_id=category.id if category else None,
                    created_at=datetime.utcnow(),
                )
                db.session.add(post)
                db.session.commit()
                return redirect(url_for("feed"))
        return render_template("post_form.html", categories=categories)

    @app.route("/post/<int:post_id>", methods=["GET"])
    def post_detail(post_id: int):
        post = Post.query.get_or_404(post_id)
        return render_template("post_detail.html", post=post)

    @app.route("/post/<int:post_id>/comment", methods=["POST"])
    @login_required
    def add_comment(post_id: int):
        post = Post.query.get_or_404(post_id)
        content = request.form.get("content", "").strip()
        if not content:
            flash("კომენტარი ცარიელია.", "error")
        else:
            comment = Comment(
                content=content, author_id=current_user.id, post_id=post.id
            )
            db.session.add(comment)
            db.session.commit()
        return redirect(url_for("post_detail", post_id=post.id))

    @app.route("/post/<int:post_id>/helpful", methods=["POST"])
    @login_required
    def helpful(post_id: int):
        post = Post.query.get_or_404(post_id)
        existing = Helpful.query.filter_by(
            user_id=current_user.id, post_id=post.id
        ).first()
        if existing:
            db.session.delete(existing)
            post.helpful_count = max(0, post.helpful_count - 1)
        else:
            db.session.add(Helpful(user_id=current_user.id, post_id=post.id))
            post.helpful_count += 1
        db.session.commit()
        return redirect(url_for("post_detail", post_id=post.id))

    @app.route("/profile/<int:user_id>")
    def profile(user_id: int):
        user = User.query.get_or_404(user_id)
        return render_template("profile.html", user=user)

    @app.route("/profile/edit", methods=["GET", "POST"])
    @login_required
    def profile_edit():
        if request.method == "POST":
            current_user.bio = request.form.get("bio", "").strip()
            current_user.achievements = request.form.get(
                "achievements", "").strip()
            current_user.projects = request.form.get("projects", "").strip()
            db.session.commit()
            return redirect(url_for("profile", user_id=current_user.id))
        return render_template("profile_edit.html")

    @app.route("/messages", methods=["GET"])
    @login_required
    def messages():
        inbox = (
            Message.query.filter_by(receiver_id=current_user.id)
            .order_by(Message.created_at.desc())
            .all()
        )
        users = User.query.filter(User.id != current_user.id).all()
        return render_template("messages.html", inbox=inbox, users=users)

    @app.route("/messages/send", methods=["POST"])
    @login_required
    def send_message():
        receiver_id = request.form.get("receiver_id", type=int)
        content = request.form.get("content", "").strip()
        if not receiver_id or not content:
            flash("მიმღები და ტექსტი სავალდებულოა.", "error")
        else:
            message = Message(
                sender_id=current_user.id, receiver_id=receiver_id, content=content
            )
            db.session.add(message)
            db.session.commit()
        return redirect(url_for("messages"))

    @app.route("/uploads/<path:filename>")
    def download_file(filename: str):
        return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

    return app


def save_file(file_storage):
    if not file_storage or not file_storage.filename:
        return None
    filename = secure_filename(file_storage.filename)
    if "." not in filename:
        return None
    ext = filename.rsplit(".", 1)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return None
    unique_name = f"{uuid4().hex}.{ext}"
    path = os.path.join(UPLOAD_FOLDER, unique_name)
    file_storage.save(path)
    return unique_name


def seed_categories() -> None:
    default_categories = [
        "მათემატიკა",
        "ფიზიკა",
        "პროგრამირება",
        "ბიოლოგია",
        "ქიმია",
        "ისტორია",
        "ქართული",
        "ინგლისური",
    ]
    existing = {c.name for c in Category.query.all()}
    for name in default_categories:
        if name not in existing:
            db.session.add(Category(name=name))
    db.session.commit()


def seed_demo_content() -> None:
    if User.query.first() or Post.query.first():
        return

    demo_users = [
        {
            "name": "ნინი კახიანი",
            "email": "nini@example.com",
            "school": "თბილისის 51-ე საჯარო სკოლა",
            "interests": "მათემატიკა, ფიზიკა",
            "bio": "ოლიმპიადებისთვის ვემზადები და მიყვარს რთული ამოცანები.",
            "achievements": "მათემატიკის ოლიმპიადა — III ადგილი (2024)",
            "projects": "მათემატიკური თამაშების სერია Python-ით",
        },
        {
            "name": "ლუკა ჯოხაძე",
            "email": "luka@example.com",
            "school": "ბათუმის 6-ე სკოლა",
            "interests": "პროგრამირება, ინგლისური",
            "bio": "ვაკეთებ სასკოლო პროექტებს და ვასწავლი თანატოლებს კოდს.",
            "achievements": "პროგრამირების კონკურსი — ფინალისტი (2023)",
            "projects": "სკოლის ბიბლიოთეკის ციფრული კატალოგი",
        },
        {
            "name": "ანი გურგენიძე",
            "email": "ani@example.com",
            "school": "ქუთაისის 1-ე საჯარო სკოლა",
            "interests": "ბიოლოგია, ქიმია",
            "bio": "ბიოლოგიის კონსპექტებს ვამზადებ და ვაზიარებ.",
            "achievements": "ბიოლოგიის ოლიმპიადა — II ადგილი (2022)",
            "projects": "ლაბორატორიული დაკვირვებების დღიური",
        },
    ]

    users = []
    for data in demo_users:
        user = User(
            name=data["name"],
            email=data["email"],
            school=data["school"],
            interests=data["interests"],
            bio=data["bio"],
            achievements=data["achievements"],
            projects=data["projects"],
        )
        user.set_password("EduConnect123!")
        db.session.add(user)
        users.append(user)
    db.session.commit()

    demo_posts = [
        {
            "title": "ოლიმპიადის ამოცანების გადაწყვეტის 3 ნაბიჯი",
            "content": (
                "როცა ამოცანა რთულია, მე ასე ვმუშაობ: 1) ვწერ ცნობილს, "
                "2) ვხაზავ სქემას, 3) ვცდილობ მარტივი მაგალითით. "
                "მაგალითად, გეომეტრიაში ხშირად გვეხმარება დამხმარე ხაზი."
            ),
            "subject": "მათემატიკა",
            "author": users[0],
        },
        {
            "title": "ფიზიკის გამოცდისთვის საჭირო თემების მოკლე სია",
            "content": (
                "გირჩევთ მოემზადოთ: მოძრაობის ტიპები, ნიუტონის კანონები, "
                "ენერგიის შენახვა, ელექტრობა და მაგნეტიზმი. "
                "მე ვაკეთებ თითო თემაზე 1 გვერდიან კონსპექტს."
            ),
            "subject": "ფიზიკა",
            "author": users[0],
        },
        {
            "title": "სასკოლო პროექტის იდეა: ამინდის პროგნოზი Python-ით",
            "content": (
                "შეგიძლია მოიძიო ღია API-დან ამინდის მონაცემები, "
                "გააკეთო პატარა ვებ-გვერდი და დაამატო გრაფიკები. "
                "პროექტი კარგად ჩანს CV-ში."
            ),
            "subject": "პროგრამირება",
            "author": users[1],
        },
        {
            "title": "ბიოლოგიის კონსპექტი: უჯრედის მემბრანა",
            "content": (
                "მოკლედ: ფოსფოლიპიდური ბილაიერი, ცილები, ტრანსპორტი "
                "და სიგნალები. შეკითხვებში ხშირად გვხვდება ოსმოზი და დიფუზია."
            ),
            "subject": "ბიოლოგია",
            "author": users[2],
        },
        {
            "title": "ქიმიის რჩევა: რეაქციების ტიპების დამახსოვრება",
            "content": (
                "მე ვიყენებ ფერად ბარათებს: სინთეზი, დაშლა, ჩანაცვლება, "
                "იონური რეაქციები. თითოეულზე ვწერ მარტივ მაგალითს."
            ),
            "subject": "ქიმია",
            "author": users[2],
        },
        {
            "title": "ქართული ლიტერატურის ანალიზი: „ვეფხისტყაოსანი“",
            "content": (
                "მთავარი თემებია მეგობრობა, პატივი და გზა საკუთარი თავისკენ. "
                "ჩემთვის საინტერესოა, როგორ იცვლება პერსონაჟების არჩევანი."
            ),
            "subject": "ქართული",
            "author": users[1],
        },
        {
            "title": "ინგლისურის სწავლა: ყოველდღიური 10 წუთიანი ჩვევა",
            "content": (
                "ყოველ დილით ვკითხულობ მოკლე სტატიას და ვიწერ 5 ახალ სიტყვას. "
                "კვირაში ერთხელ ვაკეთებ მცირე საუბარს მეგობართან."
            ),
            "subject": "ინგლისური",
            "author": users[1],
        },
    ]

    for data in demo_posts:
        category = Category.query.filter_by(name=data["subject"]).first()
        post = Post(
            title=data["title"],
            content=data["content"],
            subject=data["subject"],
            author_id=data["author"].id,
            category_id=category.id if category else None,
            created_at=datetime.utcnow(),
        )
        db.session.add(post)
    db.session.commit()

    first_post = Post.query.first()
    if first_post:
        comment = Comment(
            content="ძალიან გამოგადგება ეს რჩევები, მადლობა გაზიარებისთვის!",
            author_id=users[1].id,
            post_id=first_post.id,
        )
        db.session.add(comment)
        db.session.commit()


app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", "5001"))
    app.run(debug=False, port=port, use_reloader=False)
