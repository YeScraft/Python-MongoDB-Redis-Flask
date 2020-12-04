from pymongo import MongoClient
from flask import Flask, render_template, url_for, request, redirect

import redis

import re  # Для работы регулярного выражения '\W+'
import datetime
import os

# для преобразовние из строки в ObjectId перед передачей в find_one
from bson.objectid import ObjectId

from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
# app.config['SECRET_KEY'] = "secret_key"    #os.getenv("SECRET_KEY")

client = MongoClient('localhost', 27017)
# db = client.ads_db
collection = client.ads_db.ads_collection

# технолоническая строка - для обнуления коллекции
# client.ads_db.ads_collection.drop()

r = redis.Redis()


@app.route("/")
def index():
    ads = collection.find().sort("date")
    ads_ls = []
    for ad in ads:
        ads_ls.append(ad)
    return render_template('index.html', ads=ads_ls)


@app.route("/make_ad", methods=['GET', 'POST'])
def make_ad():
    if request.method == 'GET':
        return render_template('make_ad.html')

    if request.method == 'POST':
        title = request.form['title']
        raw_tags = request.form['tags']
        tags = re.split('\W+', raw_tags)  # Разбиваем строку на отдельные слова с удалением символов
        ad = request.form['ad']

        new_ad = {"title": title,
                "tags": tags,
                "ad": ad,
                "comments": [],
                "date": datetime.datetime.utcnow()}

        ad_id = collection.insert_one(new_ad).inserted_id
        r.hset(str(ad_id), 'r_tags', len(tags))
        r.hset(str(ad_id), 'r_comments', 0)
        return redirect('/')


@app.route('/add_comment/<path:ad_id>', methods=['GET', 'POST'])
def add_comment(ad_id):
    if request.method == 'GET':
        return render_template('add_comment.html')

    if request.method == 'POST':
        comment = request.form['comment']
        # Преобразовываем из строки в ObjectId
        success = collection.update_one({'_id': ObjectId(ad_id)}, {'$push': {'comments': comment}})
        if success.matched_count == success.modified_count:
            r.hincrby(str(ad_id), 'r_comments', 1)
        return redirect('/')


@app.route('/add_tag/<path:ad_id>', methods=['GET', 'POST'])
def add_tag(ad_id):
    if request.method == 'GET':
        return render_template('add_tag.html')

    if request.method == 'POST':
        new_tags = request.form['tags']
        tags = re.split('\W+', new_tags)
        # $addToSet добавляет только уникальные тэги
        success = collection.update_one({'_id': ObjectId(ad_id)}, {'$addToSet': {'tags': {'$each': tags}}})
        # проверка на выполнение апперации
        if success.matched_count == success.modified_count:
            r.hincrby(str(ad_id), 'r_tags', len(tags))
        return redirect('/')


@app.route('/statistics/<path:ad_id>')
def statistics(ad_id):
    ad = collection.find_one({'_id': ObjectId(ad_id)})
    stat = {
        'r_id': ad_id,
        'r_tags': r.hget(str(ad_id), 'r_tags').decode("utf-8"),
        'r_comments': r.hget(str(ad_id), 'r_comments').decode("utf-8"),
    }
    return render_template('statistics.html', ad=ad, stat=stat)


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)
