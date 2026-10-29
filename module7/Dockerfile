# Objective 2: serve the company website out of the box with a web server.
# Builds on the official Apache httpd image, which serves files from
# /usr/local/apache2/htdocs on port 80.
FROM httpd:2.4

# Put the website (downloaded by fetch-website.sh) where httpd serves it.
COPY website/ /usr/local/apache2/htdocs/

# Objective 3: keep the website's data outside the container.
# Declaring the folder as a volume means Docker stores it outside the
# container's own filesystem. When an empty named volume is mounted here,
# Docker first copies these files into it.
VOLUME /usr/local/apache2/htdocs

EXPOSE 80
