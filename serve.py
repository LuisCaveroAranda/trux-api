"""Arrancar Fuegos Artificiales TRUX con Waitress (Windows)."""
from waitress import serve
from charito_project.wsgi import application

if __name__ == '__main__':
    print("Fuegos Artificiales TRUX corriendo en http://0.0.0.0:8080")
    serve(application, host='0.0.0.0', port=8080, threads=4)
