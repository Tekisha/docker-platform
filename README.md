## Initial system setup

On first run, the system must be initialized by creating a superadmin account.

```bash
export SUPERADMIN_PASS_FILE=./secrets/superadmin_password.txt
python manage.py migrate
python manage.py flush # optional but recommended for clean start
python manage.py setup_system
```

The generated password will be written to the file specified by `SUPERADMIN_PASS_FILE`.
On first login, the superadmin is required to change the password.
