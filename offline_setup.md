# Offline Setup & Deployment Guide

This document lists all packaging, installation, and deployment commands used to run the **PIR Intelligence Pipeline** completely offline. It is designed to support custom PyPI mirror registries, custom container yard (Docker registry) setups, and custom local paths for machine learning models.

---

## 🏗️ 1. Host Machine Packaging (Online System)

On an internet-connected system with access to PyPI, Hugging Face Hub, and GitHub, run the following steps to download and package all dependency wheels and model assets.

### Step 1: Install Pip in the Virtual Environment
To ensure wheel compatibility, pip is installed inside a Python 3.13 virtual environment:
```bash
uv pip install pip
```

### Step 2: Compile Dependencies to standard requirements.txt
Compile the dependencies listed in `pyproject.toml` into a flat `requirements.txt`:
```bash
uv pip compile pyproject.toml -o requirements.txt
```

### Step 3: Run the Packager Script
Run the package script to fetch all wheels (including build backends like `hatchling` and `editables`) and download local copies of Hugging Face repositories:
```bash
./package_offline.sh
```

#### Custom PyPI Mirror Registry:
If you have a custom PyPI registry mirror (e.g. Nexus, Artifactory, DevPi), provide the `-i` or `--index-url` flag:
```bash
./package_offline.sh --index-url "https://my-custom-pypi.internal/simple"
```

#### Custom Output Directories:
If you want to save assets to custom storage paths:
```bash
./package_offline.sh --wheels-dir "/volumes/secure-media/wheels" --model-dir "/volumes/secure-media/models"
```

This step downloads:
1. **Python Wheels (`./wheels/`)**: All application dependencies, including build systems (`hatchling` and `editables`).
2. **ML Models (`./models/`)**:
   - `nomic-ai/nomic-embed-text-v1.5` (via `huggingface_hub` snapshot)
   - `nomic-ai/nomic-bert-2048` (as a required remote code dependency)
   - `en_core_web_sm` (copied spaCy model wheel)

---

## 🛬 2. Airgap Setup & Running (Offline System)

Copy the project directory, the packaged `./wheels/` folder, and the `./models/` folder onto secure media (e.g. optical disk, secure USB) and transport them to the airgapped system.

### Step 1: Install and Run Using the Offline Script
The script `./run_offline.sh` sets the environment variable `HF_HUB_OFFLINE=1` to block outbound Hugging Face network requests and configures local loading paths.

Run the CLI pipeline offline:
```bash
./run_offline.sh -q "What is Cozy Bear doing to target pipelines?"
```

Start the FastAPI web server offline:
```bash
./run_offline.sh --server
```

#### Custom Local Paths for ML Models:
If your model files are located in a custom directory:
```bash
./run_offline.sh --model-dir "/opt/offline-models" -q "What is Cozy Bear doing to target pipelines?"
```

#### Custom Wheels Location:
If your wheels directory is located elsewhere:
```bash
./run_offline.sh --wheels-dir "/mnt/usb/wheels"
```

---

## 🐋 3. Containerized Deployment (Container Yard / Docker)

If you are deploying using Docker/Kubernetes on the airgap network, you can customize the image build and push it to a private container yard.

### Step 1: Build the Image with a Custom PyPI Mirror
To build the Docker image using a custom PyPI registry mirror, pass the build arguments to the docker build command:
```bash
docker build \
  --build-arg UV_DEFAULT_INDEX="https://my-custom-pypi.internal/simple" \
  --build-arg NOMIC_MODEL_PATH="./models/nomic-embed-text-v1.5" \
  -t pir-search:latest .
```

### Step 2: Push to a Custom Container Yard
Tag the image to point to your secure private container registry and push it:
```bash
# Tag the image with the custom container yard domain
docker tag pir-search:latest my-registry.internal/cosmic/pir-search:latest

# Push to the custom container yard
docker push my-registry.internal/cosmic/pir-search:latest
```

### Step 3: Run the Container Offline
Start the container. The preloaded Nomic model is baked into the image, making it fully operational offline:
```bash
docker run -p 8000:8000 my-registry.internal/cosmic/pir-search:latest
```
