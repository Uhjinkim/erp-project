from django.db import models


class Person(models.Model):
    person_id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=50)
    birth_date = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=1, null=True, blank=True)

    class Meta:
        db_table = "persons"


class Position(models.Model):
    position_code = models.CharField(primary_key=True, max_length=20)
    position_name = models.CharField(max_length=50)
    sort_order = models.IntegerField(default=0)

    class Meta:
        db_table = "positions"
        ordering = ["sort_order", "position_code"]


class Department(models.Model):
    dept_no = models.IntegerField(primary_key=True)
    dept_name = models.CharField(max_length=100)
    parent = models.ForeignKey(
        "self",
        db_column="parent_dept_no",
        null=True,
        blank=True,
        on_delete=models.RESTRICT,
        related_name="children",
    )
    head = models.ForeignKey(
        "Employee",
        db_column="head_emp_no",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="headed_departments",
    )

    class Meta:
        db_table = "departments"
        ordering = ["dept_no"]


class Employee(models.Model):
    class TenureStatus(models.TextChoices):
        ACTIVE = "재직", "재직"
        LEAVE = "휴직", "휴직"
        TERMINATED = "퇴사", "퇴사"

    employee_no = models.IntegerField(primary_key=True, db_column="emp_no")
    person = models.ForeignKey(
        Person,
        db_column="person_id",
        on_delete=models.RESTRICT,
        related_name="employments",
    )
    department = models.ForeignKey(
        Department,
        db_column="dept_no",
        null=True,
        blank=True,
        on_delete=models.RESTRICT,
        related_name="employees",
    )
    position = models.ForeignKey(
        Position,
        db_column="position_code",
        null=True,
        blank=True,
        on_delete=models.RESTRICT,
        related_name="employees",
    )
    tenure_status = models.CharField(max_length=20, choices=TenureStatus.choices)
    phone = models.CharField(max_length=20, null=True, blank=True)
    email = models.EmailField(max_length=100, null=True, blank=True, unique=True)
    hire_date = models.DateField()
    term_date = models.DateField(null=True, blank=True)
    extension_no = models.CharField(max_length=20, db_column="ext_no", null=True, blank=True)
    address = models.CharField(max_length=255, null=True, blank=True)
    bank_code = models.CharField(max_length=20, null=True, blank=True)
    account_no = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        db_table = "employees"
        ordering = ["employee_no"]

    @property
    def is_active_employee(self) -> bool:
        return self.tenure_status == self.TenureStatus.ACTIVE and self.term_date is None


class EmploymentHistory(models.Model):
    history_id = models.BigAutoField(primary_key=True)
    employee = models.ForeignKey(
        Employee,
        db_column="emp_no",
        on_delete=models.RESTRICT,
        related_name="employment_history",
    )
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    department = models.ForeignKey(
        Department,
        db_column="dept_no",
        on_delete=models.RESTRICT,
        related_name="employment_history",
    )
    position = models.ForeignKey(
        Position,
        db_column="position_code",
        on_delete=models.RESTRICT,
        related_name="employment_history",
    )
    base_salary = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)

    class Meta:
        db_table = "emp_history"
        ordering = ["employee_id", "-start_date"]


class Role(models.Model):
    role_code = models.CharField(primary_key=True, max_length=30)
    role_name = models.CharField(max_length=50)

    class Meta:
        db_table = "roles"
        ordering = ["role_code"]


class EmployeeRole(models.Model):
    employee_role_id = models.BigAutoField(primary_key=True)
    employee = models.ForeignKey(
        Employee,
        db_column="emp_no",
        on_delete=models.RESTRICT,
        related_name="role_assignments",
    )
    role = models.ForeignKey(
        Role,
        db_column="role_code",
        on_delete=models.RESTRICT,
        related_name="employee_assignments",
    )
    assigned_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "employee_roles"
        ordering = ["employee_id", "role_id", "-assigned_at"]
