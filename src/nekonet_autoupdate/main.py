import uvicorn
from .config import Settings
from .service import CoordinatorService
from .api.app import create_app
def run():
 s=Settings(); service=CoordinatorService(s); uvicorn.run(create_app(service,s),host=s.api_bind,port=s.api_port)
if __name__=='__main__':run()
