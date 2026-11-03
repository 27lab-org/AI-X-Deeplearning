set -e
curl -LsSf https://astral.sh/uv/install.sh | sh >/dev/null 2>&1
export PATH="$HOME/.local/bin:$PATH"
uv --version
uv venv --python 3.10 ~/venv/py310
source ~/venv/py310/bin/activate
python --version
uv pip install tensorflow==2.15.0 scipy matplotlib nibabel 2>&1 | tail -15
python -c "import tensorflow as tf, numpy; print(tf.__version__, numpy.__version__, hasattr(tf.keras.optimizers,'legacy'))" 2>&1 | tail -3
