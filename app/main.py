import os
from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
CORS(app)

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'postgresql://postgres:12345@localhost/Practice_db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class Vacancy(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    company = db.Column(db.String(150), nullable=False)
    city = db.Column(db.String(150), nullable=False)
    work_format = db.Column(db.String(150), nullable=True)
    url = db.Column(db.String(150), nullable=False, unique=True)

with app.app_context():
    db.create_all()

@app.route('/parse', methods=['POST'])
def parse():
    data = request.get_json()
    job_title, company, city, work_format = data['jobTitle'], data['company'], data['city'], data['workFormat']
    
    params = {
        'text': f'{job_title} {company} {city} {work_format}',
        'area': '1',
        'per_page': 100
    }

    response = requests.get('https://api.hh.ru/vacancies', params=params)
    if response.status_code == 200:
        data = response.json()
        results = []

        for item in data['items']:
            name = item['name']
            company = item['employer']['name']
            city = item['area']['name']
            work_format = item.get('schedule', {}).get('name', '')
            url = item['alternate_url']
            
            result = {
                "Вакансия": name,
                "Компания": company,
                "Город": city,
                "Формат работы": work_format,
                "Ссылка": url
            }
            results.append(result)
            
            if not Vacancy.query.filter_by(url=url).first():
                vacancy = Vacancy(
                    name=name,
                    company=company,
                    city=city,
                    work_format=work_format,
                    url=url
                )
                db.session.add(vacancy)
        
        db.session.commit()
        return jsonify(results)
    
    else:
        return jsonify({'error': f"Ошибка: {response.status_code}"}), response.status_code

@app.route('/vacancies', methods=['GET'])
def get_vacancies():
    filters = request.args

    query = Vacancy.query

    if filters.get('jobTitle'):
        query = query.filter(Vacancy.name.ilike(f"%{filters.get('jobTitle')}%"))
    if filters.get('company'):
        query = query.filter(Vacancy.company.ilike(f"%{filters.get('company')}%"))
    if filters.get('city'):
        query = query.filter(Vacancy.city.ilike(f"%{filters.get('city')}%"))
    if filters.get('workFormat'):
        query = query.filter(Vacancy.work_format.ilike(f"%{filters.get('workFormat')}%"))

    results = [
        {
            "Вакансия": vacancy.name,
            "Компания": vacancy.company,
            "Город": vacancy.city,
            "Формат работы": vacancy.work_format,
            "Ссылка": vacancy.url
        } for vacancy in query.all()
    ]
    return jsonify(results)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)



