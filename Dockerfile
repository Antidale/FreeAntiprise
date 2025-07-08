FROM python:3.10 AS base

WORKDIR /fe
COPY requirements.txt .
## this might still be needed for the tools site, so leaving it in
# COPY docker_fe.pth ENV/lib/python3.11/site-packages/fe.pth
RUN pip install -r requirements.txt
RUN apt-get update
RUN apt-get install -y libgtk-3-dev

# change 'ff4.rom.smc' to the rom you're using, updating the path to the file if it is not contained within this folder. do not change /fe/ff4.rom.smc at all, unless you also change the ROMs name/path down below in the CMD at the end of the file.
COPY ff4.rom.smc /fe/ff4.rom.smc
COPY f4c ./f4c/
COPY FreeEnt ./FreeEnt/
COPY .env .

# if you haven't already grab the file from: https://github.com/Alcaro/Flips/releases. be sure to rename the `flips` file contained in the `flips-linux.zip` to flips-linux, or just change the copy statement. FE does expect to see `flips-linux` in the `FreeEnt/server/bin` folder, since the container itself is linux
COPY flips-linux ./FreeEnt/server/bin
RUN chmod +x FreeEnt/server/bin/flips-linux

## Future work to have the docker file build both the main site and the tools site, and in the compose run them both.
# FROM base AS site
EXPOSE 8080
CMD ["python", "-m", "FreeEnt", "./ff4.rom.smc", "server", "--local"]

# FROM base AS tools
# EXPOSE 8082
# CMD ["python", "./fetools/tool_site.py", "./ff4.rom.smc"]
