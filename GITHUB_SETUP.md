# GitHub Token Setup Guide

## Setting up your GitHub token for easy authentication

### Step 1: Create a GitHub Personal Access Token

1. Go to GitHub → Settings → Developer settings → Personal access tokens
2. Click "Generate new token" (classic)
3. Give it a name like "News Search CLI"
4. Select scopes: `repo` (full control of private repositories)
5. Click "Generate token" and copy the token immediately

### Step 2: Configure your local git setup

#### Option A: Using .env file (recommended)

1. Edit the `.env` file in this project:
   ```bash
   nano .env
   ```

2. Replace the placeholder with your actual token:
   ```
   GITHUB_TOKEN=your_actual_github_token_here
   ```

3. Set up git credential helper:
   ```bash
   git config --global credential.helper store
   ```

4. Create credentials file:
   ```bash
   echo "https://your_github_username:$GITHUB_TOKEN@github.com" > ~/.git-credentials
   ```

#### Option B: Using SSH (alternative)

1. Generate SSH key if you don't have one:
   ```bash
   ssh-keygen -t ed25519 -C "your_email@example.com"
   ```

2. Add SSH key to GitHub:
   - Copy public key: `cat ~/.ssh/id_ed25519.pub`
   - Go to GitHub → Settings → SSH and GPG keys → New SSH key
   - Paste your public key

3. Change remote URL to SSH:
   ```bash
   git remote set-url origin git@github.com:your_username/news_search.git
   ```

### Step 3: Test your setup

```bash
# Test git operations
git pull origin main
git push origin main
```

### Security Notes

- Never commit your `.env` file (it's already in `.gitignore`)
- Keep your token secure - it provides access to your repositories
- You can revoke tokens anytime in GitHub settings
- Consider using SSH for even better security

### Troubleshooting

If you still get authentication prompts:

1. Check your token has the right permissions
2. Make sure the token hasn't expired
3. Try regenerating the token
4. Check your git remote URL: `git remote -v`
5. Try clearing cached credentials: `git credential-cache exit`