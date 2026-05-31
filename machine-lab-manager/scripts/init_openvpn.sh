#!/usr/bin/env bash
set -e

EASYRSA_DIR=/etc/openvpn/easy-rsa
PKI_DIR="$EASYRSA_DIR/pki"
CCD_DIR=/etc/openvpn/ccd

# Only initialize if the CA cert isn't already there
if [ ! -f "$PKI_DIR/ca.crt" ]; then
  echo "Initializing OpenVPN PKI…"

  # If an empty PKI_DIR was created by Docker, remove it so easyrsa can init
  if [ -d "$PKI_DIR" ] && [ ! -s "$PKI_DIR" ]; then
    rm -rf "$PKI_DIR"
  fi

  cd "$EASYRSA_DIR"

  # Non-interactive mode: either export EASYRSA_BATCH=1 or pass --batch
  # Here we use the --batch flag on each call.
  ./easyrsa --batch init-pki
  ./easyrsa --batch build-ca nopass
  ./easyrsa gen-dh
  openvpn --genkey --secret ta.key

  # Build server cert, non-interactive
  ./easyrsa --batch build-server-full server nopass

  # Write the server.conf
  cat > /etc/openvpn/server.conf <<'EOF'
port 1194
proto udp
dev tun

topology subnet

ca /etc/openvpn/easy-rsa/pki/ca.crt
cert /etc/openvpn/easy-rsa/pki/issued/server.crt
key /etc/openvpn/easy-rsa/pki/private/server.key
dh /etc/openvpn/easy-rsa/pki/dh.pem
tls-auth /etc/openvpn/easy-rsa/ta.key 0

server 10.8.0.0 255.255.255.0

client-config-dir /etc/openvpn/ccd

keepalive 10 120
persist-key
persist-tun
user nobody
group nogroup
verb 3
EOF

  mkdir -p "$CCD_DIR"
  chown nobody:nogroup "$CCD_DIR"
  chmod 744 "$CCD_DIR"


  echo "OpenVPN PKI initialized."
else
  echo "OpenVPN PKI already exists, skipping init."
fi

## ensure DROP at end of FORWARD (runs every container start; ACCEPT pairs added by manager match first)
iptables -C FORWARD -i tun0 -o tun0 -j DROP 2>/dev/null || iptables -A FORWARD -i tun0 -o tun0 -j DROP
