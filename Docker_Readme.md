## Preconditions
### Docker Installation
You need Docker (or some other Docker-like, although I have not tested this in Podman or other things) installed, and it needs to be able to run from the Dockerfile and docker-compose.yml files.

### Assumptions and Assumption Remedies
The `docker-compose.yml` file assumes that:
* port 8080 on your machine is free to map to the FE Website's port.
* port 27017 on your machine is free to map to the MongoDb container's port.
* Your FF2 (US) v1.1 ROM is at in the root directory this project and is named `ff4.rom.smc`.
* You have a copy of `flips-linux` also at the root directory of this project. Get the file from https://github.com/Alcaro/Flips/releases

For the ports, if you want to change what your local machine maps those ports to, update the `docker-compose.yml` file.
For the files, either change the names of them to those assumed values, or update the relevant steps in the `Dockerfile`.

## Running things
A simple `docker compose up` should do all the magic.
Once that is done, you can navigate to http://127.0.0.1:8080/make to start generating seeds. GL HF!