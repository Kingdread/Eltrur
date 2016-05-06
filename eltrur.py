import datetime
import os
import re
import shutil
import time
from collections import namedtuple
from flask import (Flask, abort, json, render_template, request,
                   send_from_directory, url_for)
from werkzeug import secure_filename


app = Flask(__name__)
app.config.from_pyfile("settings.py")


Build = namedtuple("Build", "name jobs url")
Job = namedtuple("Job",
                 "job build tests branch commit os rust_version "
                 "travis_url all_passed upload_time url")


@app.route("/")
def index():
    builds = os.listdir(app.config["DATA_DIR"])
    builds.sort(key=natsort, reverse=True)
    builds = [Build(name=name, jobs=[], url=url_for("view_build", build=name))
              for name in builds]
    return render_template("index.html", builds=builds)


@app.route("/upload", methods=["POST"])
def upload():
    if request.form["key"] != app.config["UPLOAD_KEY"]:
        abort(403)

    report = request.files["report"].read().decode("utf-8")
    report_data = parse_report(report)
    metadata = {
        "tests": report_data,
        "branch": request.form["branch"],
        "commit": request.form["commit"],
        "build": request.form["build"],
        "job": request.form["job"],
        "os": request.form["os"],
        "rust_version": request.form["rust-version"],
        "travis_url": request.form["url"],
        "all_passed": all(test["passed"] for test in report_data),
        "upload_time": time.time(),
    }

    build_dir = secure_filename(metadata["build"])
    job_dir = secure_filename(metadata["job"])
    target_dir = os.path.join(app.config["DATA_DIR"], build_dir, job_dir)

    # Travis allows rebuilds of jobs, we don't want to reject that data
    if os.path.exists(target_dir):
        shutil.rmtree(target_dir)
    os.makedirs(target_dir, exist_ok=True)

    metadata_path = os.path.join(target_dir, "metadata")
    with open(metadata_path, "w") as metadata_file:
        json.dump(metadata, metadata_file)

    expected_filenames = {test["screenshot"] for test in metadata["tests"]}
    for shot in request.files.getlist("shots"):
        if shot.filename not in expected_filenames:
            continue
        shot_path = os.path.join(target_dir, secure_filename(shot.filename))
        shot.save(shot_path)

    return url_for(
        "view_single_job",
        build=metadata["build"],
        job=metadata["job"],
    )


@app.route("/build/<build>")
def view_build(build):
    build_dir = os.path.join(app.config["DATA_DIR"], secure_filename(build))
    try:
        jobs = os.listdir(build_dir)
    except FileNotFoundError:
        abort(404)
    jobjects = []
    for job in jobs:
        metadata_path = os.path.join(build_dir, job, "metadata")
        with open(metadata_path) as metadata_file:
            metadata = json.load(metadata_file)
        job = create_job(metadata)
        jobjects.append(job)
    jobjects.sort(key=lambda j: natsort(j.job))
    build = Build(
        name=build,
        jobs=jobjects,
        url=url_for("view_build", build=build),
    )
    return render_template(
        "single_build.html",
        title="Build #{}".format(build.name),
        build=build,
    )



@app.route("/build/<build>/job/<job>")
def view_single_job(build, job):
    job_dir = os.path.join(app.config["DATA_DIR"], secure_filename(build),
                           secure_filename(job))
    try:
        with open(os.path.join(job_dir, "metadata")) as metadata_file:
            metadata = json.load(metadata_file)
    except IOError:
        abort(404)
    job = create_job(metadata)

    return render_template(
        "single_job.html",
        title="Job {}".format(job.job),
        job=job,
    )


@app.route("/build/<build>/job/<job>/image/<test>")
def screenshot(build, job, test):
    job_dir = os.path.join(app.config["DATA_DIR"], secure_filename(build),
                           secure_filename(job))
    return send_from_directory(job_dir, test, as_attachment=True)


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


def natsort(string):
    parts = re.split("(\\d+)", string)
    result = []
    for part in parts:
        try:
            result.append(int(part))
        except ValueError:
            result.append(part)
    return result


def create_job(obj):
    # Copy the dict
    obj = dict(obj)
    obj["upload_time"] = datetime.datetime.fromtimestamp(obj["upload_time"])
    obj["build"] = Build(obj["build"], [], url_for("view_build",
                                                   build=obj["build"]))
    obj["url"] = url_for("view_single_job", build=obj["build"].name,
                         job=obj["job"])
    return Job(**obj)


if __name__ == "__main__":
    app.run(debug=True)
