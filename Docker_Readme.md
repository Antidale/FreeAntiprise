## Preconditions
### Docker Installation
You need Docker (or some other Docker-like, although I have not tested this in Podman or other things) installed, and it needs to be able to run from the Dockerfile and docker-compose.yml files.

### Assumptions and Assumption Remedies
The `docker-compose.yml` file assumes that:
* port 8080 on your machine is free to map to the FE Website's port.
* port 8082 on your machine is free to mape to the tools site's port.
* port 27017 on your machine is free to map to the MongoDb container's port.

if you have port conflicts, you can change the first number of the entry in the docker-compose.yml like so:
```yml
    ports:
      - "8081:8080"
```
However, and especially in the case of the main website, this can lead to some expected functionality breaking, like when you click on the flags on the patch page to get back to the `/make` page with your flagset pre-populated to generate another seed.

* Your FF2 (US) v1.1 ROM is at in the root directory this project and is named `ff4.rom.smc`. If you want to keep your file name, just change `COPY ff4.rom.smc /app/ff4.rom.smc` command to read `COPY your-file-name.smc /app/ff4.rom.smc`. Changing both instances of `ff4.rom.smc` there would require other changes further on in the Dockerfile, so don't do that.

For the ports, if you want to change what your local machine maps those ports to, update the `docker-compose.yml` file.
For the files, either change the names of them to those assumed values, or update the relevant steps in the `Dockerfile`.

## Running things
A simple `docker compose up --build` should do all the magic.
Once that is done, you can navigate to http://127.0.0.1:8080/make to start generating seeds. GL HF!

If you want to use the tools site, just navigate to http://127.0.0.1:8082/
