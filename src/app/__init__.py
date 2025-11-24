'''
Docstring
'''
from fastapi import FastAPI
from app.localAllocationManager.routers import router

# FastAPI object customization
FASTAPI_TITLE = "hlo-deployment-engine"
FASTAPI_DESCRIPTION = "HLO component addressing LLO for service components deployment"
FASTAPI_VERSION = "0.109.0"
FASTAPI_OPEN_API_URL = "/docs"
FASTAPI_DOCS_URL = "/"

app = FastAPI(title=FASTAPI_TITLE,
              description=FASTAPI_DESCRIPTION,
              version=FASTAPI_VERSION,
              docs_url=FASTAPI_DOCS_URL,
              openapi_url=FASTAPI_OPEN_API_URL)
app.include_router(router=router, tags=["hlo-deplyment-engine"])
