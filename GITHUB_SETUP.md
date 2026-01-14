# GitHub Setup with PAT (Personal Access Token)

## Setting Remote URL with PAT

To use a Personal Access Token (PAT) for authentication, you have two options:

### Option 1: Set Remote URL with PAT (Recommended)

Replace `YOUR_PAT_TOKEN` with your actual Personal Access Token:

```bash
git remote set-url origin https://YOUR_PAT_TOKEN@github.com/voiceofarsalan/Enatega_Estimation_Bot.git
```

### Option 2: Use Git Credential Helper (More Secure)

This stores your credentials securely:

```bash
# Set remote URL (without PAT in URL)
git remote set-url origin https://github.com/voiceofarsalan/Enatega_Estimation_Bot.git

# Configure credential helper to store PAT
git config --global credential.helper store

# On first push, Git will prompt for username and password
# Username: your-github-username
# Password: YOUR_PAT_TOKEN
```

### Option 3: Use SSH (Alternative)

If you prefer SSH:

```bash
git remote set-url origin git@github.com:voiceofarsalan/Enatega_Estimation_Bot.git
```

## Creating a PAT

If you don't have a PAT yet:

1. Go to GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Click "Generate new token (classic)"
3. Give it a name (e.g., "Estimate_Bot_Repo")
4. Select scopes: `repo` (full control of private repositories)
5. Click "Generate token"
6. Copy the token immediately (you won't see it again)

## Initial Push

After setting up the remote:

```bash
# Add all files
git add .

# Commit
git commit -m "Initial commit: Estimation Bot with intelligent AI analysis"

# Push to GitHub
git push -u origin main
```

## Current Remote Configuration

Current remote URL: `https://github.com/voiceofarsalan/Enatega_Estimation_Bot.git`

To update with PAT:
```bash
git remote set-url origin https://YOUR_PAT_TOKEN@github.com/voiceofarsalan/Enatega_Estimation_Bot.git
```
