FROM hub.cc-asp.fraunhofer.de/simpartixpublic/simpartix:05

# add source code from the repository that includes all source files
ADD simpartix /source
WORKDIR /source/code
RUN make -j 4
WORKDIR /source/ProPARTIX/code
RUN make
ENV PATH="${PATH}:/source/code/"
ENV PYTHONPATH "${PYTHONPATH}:/source/ProPARTIX/code"
ENV PROPARTIXPATH "/source/ProPARTIX/code"
WORKDIR /app
# To store the files from the simulations
RUN mkdir simulation_files
ADD requirements.txt  .
RUN pip install -r requirements.txt
ADD models ./models
ADD simpartix  ./simpartix
ADD simulation_controller ./simulation_controller
ADD static ./static
ADD app.py .


CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]

# docker compose up
