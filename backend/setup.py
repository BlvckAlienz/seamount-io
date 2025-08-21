from setuptools import setup, find_packages

setup(
    name="seamount-backend",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "fastapi",
        "gunicorn",
        "uvicorn[standard]",
        "supabase",
        "aiohttp",
        "fastapi-mail",
        "passlib[bcrypt]",
        "python-jose[cryptography]",
        "python-multipart",
        "python-dotenv",
        "pydantic",
        "tenacity",
        "pyotp",
        "py-algorand-sdk",
        "pydantic-settings",
        "complycube",
    ],
)