
FROM public.ecr.aws/lambda/python:3.10

# System dependencies
RUN yum install -y gcc gcc-c++ python3-devel openssl-devel wget make tar gzip

# Install CMake
RUN wget https://github.com/Kitware/CMake/releases/download/v3.26.4/cmake-3.26.4-linux-x86_64.tar.gz &&     tar xzf cmake-3.26.4-linux-x86_64.tar.gz -C /usr/local --strip-components=1 &&     rm cmake-3.26.4-linux-x86_64.tar.gz

# 🔧 Install dependencies in correct order
RUN pip install --upgrade pip &&     pip install numpy &&     pip install pybind11 tenseal --no-cache-dir

# Copy app code
COPY app.py ${LAMBDA_TASK_ROOT}

# Lambda entry point
CMD ["app.lambda_handler"]

