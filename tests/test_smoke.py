"""Automated smoke tests for core application access and student creation."""
import os
import tempfile
import unittest

from app import create_app, db, College, User, Student


class ApplicationTests(unittest.TestCase):
    def setUp(self):
        handle, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(handle)
        self.app = create_app({
            "TESTING": True,
            "WTF_CSRF_ENABLED": False,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{self.db_path}",
            "RATELIMIT_ENABLED": False,
            "SECRET_KEY": "test-only-secret",
        })
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        self.college = College(name="Test College", code="TEST")
        db.session.add(self.college)
        db.session.flush()
        self.admin = User(college_id=self.college.id, full_name="Test Admin",
                          email="admin@test.local", role="admin")
        self.admin.set_password("Test-Password-123!")
        db.session.add(self.admin)
        db.session.commit()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()
        try:
            os.unlink(self.db_path)
        except OSError:
            pass

    def login(self):
        return self.client.post("/login", data={
            "email": "admin@test.local", "password": "Test-Password-123!"
        }, follow_redirects=True)

    def test_health_endpoint(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "ok")

    def test_dashboard_requires_login(self):
        response = self.client.get("/dashboard")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.headers["Location"])

    def test_admin_can_create_student(self):
        self.login()
        response = self.client.post("/m/students", data={
            "student_no": "GPGC-2026-001", "first_name": "Amina",
            "last_name": "Khan", "father_name": "Test Parent",
            "email": "student@example.test", "phone": "03000000000",
            "program": "BS Computer Science", "semester": "1",
            "admission_date": "2026-10-01", "status": "Accepted",
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        student = Student.query.filter_by(student_no="GPGC-2026-001").first()
        self.assertIsNotNone(student)
        self.assertEqual(student.college_id, self.college.id)

    def test_duplicate_student_number_is_not_created_twice(self):
        self.login()
        payload = {
            "student_no": "DUP-1", "first_name": "Ali", "last_name": "",
            "father_name": "", "email": "", "phone": "", "program": "",
            "semester": "", "admission_date": "2026-10-01", "status": "Applied",
        }
        self.client.post("/m/students", data=payload, follow_redirects=True)
        self.client.post("/m/students", data=payload, follow_redirects=True)
        self.assertEqual(Student.query.filter_by(student_no="DUP-1").count(), 1)

    def test_teacher_cannot_access_admissions(self):
        teacher = User(college_id=self.college.id, full_name="Teacher",
                       email="teacher@test.local", role="teacher")
        teacher.set_password("Teacher-Password-123!")
        db.session.add(teacher)
        db.session.commit()
        self.client.post("/login", data={
            "email": "teacher@test.local", "password": "Teacher-Password-123!"
        })
        self.assertEqual(self.client.get("/m/students").status_code, 403)


if __name__ == "__main__":
    unittest.main()
