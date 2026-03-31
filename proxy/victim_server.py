from fastapi import FastAPI
import uvicorn

app = FastAPI(title="VICTIM WEB SERVER")

@app.api_route("/{path:path}", methods=["GET", "POST"])
async def catch_all(path: str):
    return {
        "status": "Success!",
        "message": "Welcome to Syncora",
        "path_accessed": f"/{path}"
    }

if __name__ == "__main__":
    print("="*50)
    print(" DECOY SERVER RUNNING ON PORT 5001...")
    print("="*50)
    uvicorn.run("victim_server:app", host="0.0.0.0", port=5001)