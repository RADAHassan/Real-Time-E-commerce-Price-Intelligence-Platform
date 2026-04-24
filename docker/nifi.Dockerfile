FROM apache/nifi:1.25.0

# Copy custom NiFi templates at build time (Phase 3)
COPY nifi/templates/ /opt/nifi/nifi-current/conf/templates/

USER nifi
