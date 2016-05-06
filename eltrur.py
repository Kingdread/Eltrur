import datetime
import os
import re
import time
from flask import (Flask, abort, json, render_template, request,
                   send_from_directory, url_for)
from werkzeug import secure_filename


app = Flask(__name__)
app.config.from_pyfile("settings.py")


@app.route("/")
def index():
    builds = os.listdir(app.config["DATA_DIR"])
    builds.sort(key=natsort)
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
        "rust-version": request.form["rust-version"],
        "url": request.form["url"],
        "all-passed": all(test["passed"] for test in report_data),
        "upload-time": time.time(),
    }

    build_dir = secure_filename(metadata["build"])
    job_dir = secure_filename(metadata["job"])
    target_dir = os.path.join(app.config["DATA_DIR"], build_dir, job_dir)

    if os.path.exists(target_dir):
        abort(418)
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
        view_single_job,
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
    job_data = {}
    for job in jobs:
        metadata_path = os.path.join(build_dir, job, "metadata")
        with open(metadata_path) as metadata_file:
            metadata = json.load(metadata_file)
        metadata_scheme(metadata)
        job_data[job] = metadata
    return render_template(
        "single_build.html",
        title="build #{}".format(build),
        build=build,
        jobs=sorted(job_data.items(), key=lambda t: (natsort(t[0]), t[1])),
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
    metadata_scheme(metadata)

    return render_template(
        "single_job.html",
        title="Job {}".format(job),
        job=job,
        build=build,
        data=metadata,
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


def metadata_scheme(obj):
    obj["upload-time"] = datetime.datetime.fromtimestamp(obj["upload-time"])
    return obj


if __name__ == "__main__":
    app.run(debug=True)
