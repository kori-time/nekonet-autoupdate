from __future__ import annotations
import uvicorn
from .config import Settings
from .service import CoordinatorService
from .api.app import create_app

def run():
    settings=Settings()
    service=CoordinatorService(settings)
    app=create_app(service,settings)
    uvicorn.run(app,host=settings.api_bind,port=settings.api_port)

if __name__=="__main__":
    run()
