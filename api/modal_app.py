"""Modal deployment wrapper. Deploy with: modal deploy api/modal_app.py"""
import modal

app = modal.App("flavornet-api")
volume = modal.Volume.from_name("flavornet-data")

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "fastapi[standard]",
        "torch",
        "torch-geometric",
        "pandas",
        "pyarrow",
        "anthropic",
        "scikit-learn",
        "numpy",
    )
    .add_local_python_source("api", "scoring", "graph", "model")
)


@app.function(
    image=image,
    volumes={"/data": volume},
    secrets=[modal.Secret.from_name("flavornet-secrets")],
    timeout=300,
)
@modal.asgi_app()
def serve():
    from api.main import fastapi_app
    return fastapi_app
