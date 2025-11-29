pushd frontend
npm install
npm run build
popd

uv pip install .
docker compose buildgi