from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from chacra.models.binaries import Binary


router = APIRouter(
    prefix="/search",
    tags=["search"],
)


@router.get("/", response_model=List[Dict])
async def search(request: Request):
    valid_params = {
        "distro", "distro_version", "arch", "ref", "built_by", "size",
        "name", "name_has"
    }
    for param in request.query_params.keys():
        if param not in valid_params:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid query parameter: {param}"
            )

    filters = []
    for param in request.query_params.keys():
        if request.query_params[param]:
            if param == "name_has":
                filters.append(Binary.name.contains(request.query_params[param]))
            else:
                filters.append(getattr(Binary, param) ==
                               request.query_params[param])

    if len(filters) == 0:
        return JSONResponse(status_code=200, content={})

    binaries = await Binary.filter(*filters)
    results = []
    for binary in binaries:
        results.append(binary.as_dict())

    return results
