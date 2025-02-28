import PyInstaller.__main__
import os
import shutil
import sys
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def build_exe():
    logger.info("Starting build process...")
    
    # Clean previous builds
    if os.path.exists('build'):
        logger.info("Removing existing build directory...")
        shutil.rmtree('build')
    if os.path.exists('dist'):
        logger.info("Removing existing dist directory...")
        shutil.rmtree('dist')

    # List all Python paths
    logger.info("Python paths:")
    for path in sys.path:
        logger.info(f"  {path}")

    logger.info("Creating executable...")
    
    # Create executable with more explicit imports
    PyInstaller.__main__.run([
        'app.py',
        '--name=DocumentationScraper',
        '--onefile',
        '--add-data=static;static',
        '--hidden-import=uvicorn',
        '--hidden-import=uvicorn.logging',
        '--hidden-import=uvicorn.protocols',
        '--hidden-import=uvicorn.lifespan',
        '--hidden-import=uvicorn.protocols.http',
        '--hidden-import=uvicorn.loops',
        '--hidden-import=uvicorn.loops.auto',
        '--hidden-import=uvicorn.protocols.http.auto',
        '--hidden-import=uvicorn.protocols.websockets.auto',
        '--hidden-import=uvicorn.logging',
        '--hidden-import=uvicorn.loops.asyncio',
        '--hidden-import=fastapi',
        '--hidden-import=fastapi.applications',
        '--hidden-import=fastapi.responses',
        '--hidden-import=fastapi.routing',
        '--hidden-import=starlette',
        '--hidden-import=starlette.routing',
        '--hidden-import=starlette.responses',
        '--hidden-import=starlette.middleware',
        '--collect-all=uvicorn',
        '--collect-all=fastapi',
        '--collect-all=starlette',
        '--debug=all'
    ])
    
    logger.info("Build process completed.")

if __name__ == '__main__':
    try:
        build_exe()
    except Exception as e:
        logger.error(f"Build failed with error: {e}", exc_info=True) 