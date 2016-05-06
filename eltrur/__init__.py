import datetime
import mimetypes
from collections import namedtuple
from flask import (Flask, abort, json, make_response, render_template, request,
                   url_for)


app = Flask(__name__, instance_relative_config=True)
app.config.from_pyfile("settings.py")


from .database import *


@app.route("/")
def index():
    builds = Build.query.all()
    builds.sort(key=lambda build: natsort(build.name), reverse=True)
    return render_template("index.html", builds=builds)


@app.route("/upload", methods=["POST"])
def upload():
    if request.form["key"] != app.config["UPLOAD_KEY"]:
        abort(403)

    report = request.files["report"].read().decode("utf-8")
    report_data = parse_report(report)
    metadata = {
        "branch": request.form["branch"],
        "commit": request.form["commit"],
        "build_name": request.form["build"],
        "os": request.form["os"],
        "rust_version": request.form["rust-version"],
        "travis_url": request.form["url"],
        "all_passed": all(test["passed"] for test in report_data),
        "upload_time": datetime.datetime.now(),
    }

    build = Build.query.get(metadata["build_name"])
    if build is None:
        build = Build(name=metadata["build_name"])
        db.session.add(build)

    # Delete old data since Travis allows for rebuilds
    old_job = Job.query.get((request.form["job"], build.name))
    if old_job is not None:
        db.session.delete(old_job)

    job = Job(**metadata)
    job.name = request.form["job"]
    db.session.add(job)

    test_names = {test["screenshot"]: test for test in report_data}
    for shot in request.files.getlist("shots"):
        if shot.filename not in test_names:
            continue
        test = Test(job=job)
        test.name = test_names[shot.filename]["test"]
        test.image_name = shot.filename
        test.image = shot.read()
        test.passed = test_names[shot.filename]["passed"]
        db.session.add(test)

    db.session.commit()
    return url_for(
        "view_single_job",
        build=build.name,
        job=job.name,
    )


@app.route("/build/<build>")
def view_build(build):
    build = Build.query.get_or_404(build)
    return render_template(
        "single_build.html",
        title="Build #{}".format(build.name),
        build=build,
    )


@app.route("/build/<build>/job/<job>")
def view_single_job(build, job):
    job = Job.query.get_or_404((job, build))
    return render_template(
        "single_job.html",
        title="Job {}".format(job.name),
        job=job,
    )


@app.route("/build/<build>/job/<job>/image/<test>")
def screenshot(build, job, test):
    test = Test.query.get_or_404((test, job, build))
    mimetype = mimetypes.guess_type(test.image_name)
    if mimetype is None:
        mimetype = "application/octet-stream"
    response = make_response(test.image)
    response.headers["Content-Type"] = mimetype
    response.headers["Content-Disposition"] = ("attachment; filename={}"
                                               .format(test.image_name))
    return response


@app.errorhandler(404)
def error_404(e):
    return render_template("error_404.html", title="404"), 404


def parse_report(data):
    result = []
    lines = data.split("\n")
    for line in lines:
        if not line:
            continue
        testname, passed, screenshot = line.split("/")
        assert passed in {"ok", "fail"}
        passed = passed == "ok"
        result.append({
            "test": testname,
            "passed": passed,
            "screenshot": screenshot,
        })
    return result
