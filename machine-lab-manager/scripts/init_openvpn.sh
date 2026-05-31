#!/usr/bin/env bash
set -e

EASYRSA_DIR=/etc/openvpn/easy-rsa
PKI_DIR="$EASYRSA_DIR/pki"
CCD_DIR=/etc/openvpn/ccd

# Subnet pushed by `server` directive. /22 gives 1022 slots (was /24 = 253).
# Must stay in sync with VPN_INTERNAL_SUBNET env consumed by app/internal/vpn.py.
VPN_NETWORK="${VPN_NETWORK:-10.8.0.0}"
VPN_NETMASK="${VPN_NETMASK:-255.255.252.0}"

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

  # Write the server.conf (envsubst-style — heredoc without quotes expands $VARS)
  cat > /etc/openvpn/server.conf <<EOF
port 1194
proto udp
dev tun

topology subnet

ca /etc/openvpn/easy-rsa/pki/ca.crt
cert /etc/openvpn/easy-rsa/pki/issued/server.crt
key /etc/openvpn/easy-rsa/pki/private/server.key
dh /etc/openvpn/easy-rsa/pki/dh.pem
tls-auth /etc/openvpn/easy-rsa/ta.key 0

server ${VPN_NETWORK} ${VPN_NETMASK}

client-config-dir /etc/openvpn/ccd

# Loopback-only management interface so the siberbox manager can kick clients
# after CCD changes (e.g. iroute additions for multi-service labs).
management 127.0.0.1 7505

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

## ensure management interface is enabled on existing deployments (idempotent)
if [ -f /etc/openvpn/server.conf ] && ! grep -q '^management ' /etc/openvpn/server.conf; then
  echo 'management 127.0.0.1 7505' >> /etc/openvpn/server.conf
  echo "appended management directive to existing server.conf"
fi

## ensure server.conf `server` line matches the desired subnet (idempotent)
if [ -f /etc/openvpn/server.conf ]; then
  EXPECTED_LINE="server ${VPN_NETWORK} ${VPN_NETMASK}"
  if ! grep -qF "$EXPECTED_LINE" /etc/openvpn/server.conf; then
    sed -i "s|^server [0-9.]\+ [0-9.]\+|${EXPECTED_LINE}|" /etc/openvpn/server.conf
    echo "rewrote server subnet line to: $EXPECTED_LINE"
  fi
fi

## rewrite existing CCD ifconfig-push netmasks to match the current subnet so
## already-issued user/.ovpn certs keep working across a subnet bump.
if [ -d "$CCD_DIR" ]; then
  for f in "$CCD_DIR"/*; do
    [ -f "$f" ] || continue
    sed -i "s|^ifconfig-push \([0-9.]\+\) [0-9.]\+|ifconfig-push \1 ${VPN_NETMASK}|" "$f"
  done
fi
