# EduConnect

EduConnect არის სპეციალიზებული სოციალური პლატფორმა ქართული სტუდენტებისთვის, რომელიც ეხმარება აკადემიურ ქსელირებას, რესურსების გაზიარებას და ოლიმპიადებისთვის/პროექტებისთვის მომზადებას.   

EduConnect is a focused academic social platform for Georgian students, centered on networking, resource sharing, and preparation for olympiads and projects.         

## ფუნქციები / Features 
 
- ავთენტიფიკაცია (რეგისტრაცია/შესვლა) / Authentication (sign up/login)    
- თემატური პოსტები და ფილტრები / Subject-based posts & filter 
- კომენტარები / Comments
- აკადემიური პროფილები (მიღწევები და პროექტები) / Academic profiles
- რესურსების ბმულები და ფაილების ატვირთვა / Resource links & uploads 
- პირადი შეტყობინებები / Private messages  
 
## ადგილობრივი გაშვება / Local setup  
  
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

აპლიკაცია გაიხსნება / Open: `http://127.0.0.1:5000`

## დემო მომხმარებლები / Demo users

პირველ გაშვებაზე ემატება საცდელი მონაცემები. პაროლი ყველა მათთვის არის: `EduConnect123!`

- nini@example.com
- luka@example.com
- ani@example.com

## გარემოს ცვლადები / Environment variables

შექმენი `.env` ფაილი / Create `.env`:

```
SECRET_KEY=your-secret-key
DATABASE_URL=sqlite:///educonnect.db
```

## დეპლოი / Deployment (Render/Railway)

- დააყენე `requirements.txt` / Install dependencies
- მიუთითე `python app.py` როგორც start command / Use `python app.py` as start command
- დაამატე `SECRET_KEY` და `DATABASE_URL` გარემოს ცვლადებად / Set env vars
- თუ იყენებ SQLite-ს, Render-ზე რეკომენდებულია PostgreSQL-ის გამოყენება / For Render, prefer PostgreSQL

## სტრუქტურა / Structure

```
.
├── app.py
├── models.py
├── requirements.txt
├── templates/
├── static/
└── uploads/
```

## ლოგო / Logo

დაამატე ოფიციალური ლოგო ფაილში: `static/tbc-logo.png`
