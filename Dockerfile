FROM node:latest

RUN mkdir /home/genai
RUN mkdir /usr/genai

RUN groupadd -g 10001 genai && \
    useradd -u 10000 -g genai -d /home/genai genai \
    && chown -R genai:genai /usr/genai \
    && chown -R genai:genai /home/genai

USER genai:genai

RUN curl -s -L https://raw.githubusercontent.com/oracle/oci-cli/master/scripts/install/install.sh -o /home/genai/oci-cli-install.sh
RUN chmod u+x /home/genai/oci-cli-install.sh

RUN /home/genai/oci-cli-install.sh --accept-all-defaults

RUN exec -l $SHELL