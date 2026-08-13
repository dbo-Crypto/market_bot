# Deploy market_bot on an OVH VPS

Paper desk only. Virtual **$1,000**. No broker login, no IBKR key, no live order.

This is a **separate** desk from `prediction_bot`. Same machine is fine: this one uses ports **3001** and **8002**.

## Ports

| Service | Host port |
|---|---|
| UI | 3002 (3001 is taken by ProtectYourDoc Uptime Kuma) |
| API / WebSocket | 8002 |

On this OVH box, start with the lean file so `next dev` does not eat RAM:

```bash
docker compose -f docker-compose.vps.yml up -d --build
```

## 1. Server once

If Docker is not installed yet (skip if you already did this for `prediction_bot`):

```bash
sudo apt-get update
sudo apt-get install -y git ca-certificates curl
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker "$USER"
# log out and back in so docker works without sudo
```

```bash
sudo ufw allow OpenSSH
sudo ufw allow 3001/tcp
sudo ufw allow 8002/tcp
sudo ufw enable
```

## 2. Clone on the VPS

The Mac deploy keys do **not** live on the VPS. Create a read-only key on the server:

```bash
ssh-keygen -t ed25519 -C "market_bot-vps" -f ~/.ssh/market_bot_vps -N ""
cat ~/.ssh/market_bot_vps.pub
```

On GitHub: repo **Settings → Deploy keys → Add deploy key**. Title `market_bot vps`. Paste the public key. Leave **Allow write access** unchecked.

Then:

```bash
mkdir -p ~/.ssh
cat >> ~/.ssh/config <<'EOF'
Host github.com-market
  HostName github.com
  User git
  IdentityFile ~/.ssh/market_bot_vps
  IdentitiesOnly yes
EOF
chmod 600 ~/.ssh/config

cd ~
git clone git@github.com-market:dbo-Crypto/market_bot.git
cd market_bot
```

## 3. Env file (never commit)

```bash
cp .env.example .env
chmod 600 .env
```

If you will open the UI from your laptop browser against the public IP, set the three host URLs. Replace `YOUR_VPS_IP` with the VPS IPv4 or hostname (`vps-43564666.vps.ovh.net`):

```bash
# in .env
CORS_ORIGINS=http://YOUR_VPS_IP:3001
NEXT_PUBLIC_API_URL=http://YOUR_VPS_IP:8002
NEXT_PUBLIC_WS_URL=ws://YOUR_VPS_IP:8002/ws
```

No broker keys. Prices come from Stooq/Yahoo (ETFs) and Binance public API (crypto).

`DATABASE_URL` / `REDIS_URL` stay as in `.env.example`.

## 4. Start

```bash
docker compose up -d --build
docker compose ps
curl -sS http://127.0.0.1:8002/health
```

Open `http://YOUR_VPS_IP:3001`.

Paper ledger lives in the Docker volume `pgdata`. `docker compose down` keeps it. `docker compose down -v` wipes the bankroll.

## 5. Update later

```bash
cd ~/market_bot
git pull
docker compose up -d --build
```

## SSH tunnel (no public UI ports)

From your Mac, with the OVH key:

```bash
ssh -i ~/.ssh/ovh/pyd -L 3001:127.0.0.1:3001 -L 8002:127.0.0.1:8002 ubuntu@vps-43564666.vps.ovh.net
```

Keep `.env` on `localhost` URLs. Open http://localhost:3001 on the Mac.

## Live France note

This paper bot can hold US tickers (`SPY`, `QQQ`). A **live** France retail account generally cannot buy those US ETFs (PRIIPs / KID). Live would use UCITS twins through a broker such as IBKR Ireland. See `procedure_live.pdf`. That path is not a switch in this repo.
