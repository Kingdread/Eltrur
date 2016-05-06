import re
from flask_sqlalchemy import SQLAlchemy
from . import app

db = SQLAlchemy(app)


class Build(db.Model):
    __tablename__ = "build"

    name = db.Column(db.String(255), primary_key=True)
    jobs = db.relationship("Job", backref="build", cascade="all",
                           order_by="Job.name")

    def sorted_jobs(self):
        return sorted(self.jobs, key=lambda job: natsort(job.name))

    def failed_jobs(self):
        return [job for job in self.jobs if not job.all_passed]


class Job(db.Model):
    __tablename__ = "job"

    name = db.Column(db.String(255), primary_key=True)
    branch = db.Column(db.String(255))
    commit = db.Column(db.String(255))
    build_name = db.Column(db.String(255), db.ForeignKey("build.name"),
                           primary_key=True)
    os = db.Column(db.String(255))
    rust_version = db.Column(db.String(255))
    travis_url = db.Column(db.String(511))
    all_passed = db.Column(db.Boolean)
    upload_time = db.Column(db.DateTime)
    tests = db.relationship("Test", backref="job", cascade="all",
                            order_by="Test.name")


class Test(db.Model):
    __tablename__ = "test"

    name = db.Column(db.String(255), primary_key=True)
    passed = db.Column(db.Boolean)
    image_name = db.Column(db.String(255))
    image = db.Column(db.LargeBinary)
    job_name = db.Column(db.String(255), primary_key=True)
    build_name = db.Column(db.String(255), primary_key=True)

    __table_args__ = (
        db.ForeignKeyConstraint([job_name, build_name],
                                [Job.name, Job.build_name]),
    )


def natsort(string):
    parts = re.split("(\\d+)", string)
    result = []
    for part in parts:
        try:
            result.append(int(part))
        except ValueError:
            result.append(part)
    return result


__all__ = ["db", "Build", "Job", "Test", "natsort"]
