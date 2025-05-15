import os
from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
CORS(app)

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL',
                                                        'postgresql://postgres:12345@localhost/Practice_db')
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

def build_search_params(job_title, company, city, work_format):
    return {
        'text': f'{job_title} {company} {city} {work_format}',
        'area': '1',
        'per_page': 100
    }

def extract_vacancy_data(item):
    return {
        "Вакансия": item['name'],
        "Компания": item['employer']['name'],
        "Город": item['area']['name'],
        "Формат_работы": item.get('schedule', {}).get('name', ''),
        "Ссылка": item['alternate_url']
    }

def save_vacancy_if_not_exists(vacancy_data):
    if not Vacancy.query.filter_by(url=vacancy_data["Ссылка"]).first():
        new_vacancy = Vacancy(
            name=vacancy_data["Вакансия"],
            company=vacancy_data["Компания"],
            city=vacancy_data["Город"],
            work_format=vacancy_data["Формат работы"],
            url=vacancy_data["Ссылка"]
        )
        db.session.add(new_vacancy)

def filter_vacancies(query, filters):
    if filters.get('jobTitle'):
        query = query.filter(Vacancy.name.ilike(f"%{filters.get('jobTitle')}%"))
    if filters.get('company'):
        query = query.filter(Vacancy.company.ilike(f"%{filters.get('company')}%"))
    if filters.get('city'):
        query = query.filter(Vacancy.city.ilike(f"%{filters.get('city')}%"))
    if filters.get('workFormat'):
        query = query.filter(Vacancy.work_format.ilike(f"%{filters.get('workFormat')}%"))
    return query

def format_vacancy_output(vacancy):
    return {
        "Вакансия": vacancy.name,
        "Компания": vacancy.company,
        "Город": vacancy.city,
        "Формат работы": vacancy.work_format,
        "Ссылка": vacancy.url
    }


@app.route('/parse', methods=['POST'])
def parse():
    data = request.get_json()
    params = build_search_params(
        job_title=data['jobTitle'],
        company=data['company'],
        city=data['city'],
        work_format=data['workFormat']
    )

    response = requests.get('https://api.hh.ru/vacancies', params=params)
    if response.status_code != 200:
        return jsonify({'error': f"Ошибка: {response.status_code}"}), response.status_code

    data = response.json()
    results = []

    for item in data['items']:
        vacancy_data = extract_vacancy_data(item)
        results.append(vacancy_data)
        save_vacancy_if_not_exists(vacancy_data)

    db.session.commit()
    return jsonify(results)

@app.route('/vacancies', methods=['GET'])
def get_vacancies():
    filters = request.args
    query = filter_vacancies(Vacancy.query, filters)
    results = [format_vacancy_output(v) for v in query.all()]
    return jsonify(results)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)



