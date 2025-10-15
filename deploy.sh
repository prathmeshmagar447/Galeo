name: 🚀 Deploy to EC2

on:
  push:
    branches:
      - main
  workflow_dispatch:

jobs:
  deploy:
    name: Deploy to EC2
    runs-on: ubuntu-latest

    steps:
      - name: ✅ Checkout repository
        uses: actions/checkout@v4

      - name: 🔑 Set up SSH
        run: |
          mkdir -p ~/.ssh
          echo "${{ secrets.EC2_SSH_KEY }}" > ~/.ssh/id_rsa
          chmod 600 ~/.ssh/id_rsa
          ssh-keyscan -H ${{ secrets.EC2_HOST }} >> ~/.ssh/known_hosts

      - name: 🧩 Create .env file dynamically
        run: |
          cat <<EOF > .env
ENV=${{ secrets.ENV }}
EC2_USERNAME=${{ secrets.EC2_USERNAME }}
OPENAI_API_KEY=${{ secrets.OPENAI_API_KEY }}
DATABASE_URL=${{ secrets.DATABASE_URL }}
AWS_ACCESS_KEY_ID=${{ secrets.AWS_ACCESS_KEY_ID }}
AWS_SECRET_ACCESS_KEY=${{ secrets.AWS_SECRET_ACCESS_KEY }}
AWS_S3_BUCKET=${{ secrets.AWS_S3_BUCKET }}
AWS_REGION=${{ secrets.AWS_REGION }}
FLASK_SECRET_KEY=${{ secrets.FLASK_SECRET_KEY }}
EOF

      - name: 🚚 Sync files to EC2 (faster & safer)
        env:
          EC2_HOST: ${{ secrets.EC2_HOST }}
          EC2_USERNAME: ${{ secrets.EC2_USERNAME }}
        run: |
          echo "⚡ Syncing files to EC2..."
          rsync -avz --delete \
            --exclude '.git' \
            --exclude '.github' \
            --exclude 'venv' \
            --exclude '__pycache__' \
            -e "ssh -i ~/.ssh/id_rsa -o StrictHostKeyChecking=no" \
            ./ $EC2_USERNAME@$EC2_HOST:/home/ubuntu/app
          
          echo "📦 Copying environment file..."
          scp -i ~/.ssh/id_rsa -o StrictHostKeyChecking=no .env $EC2_USERNAME@$EC2_HOST:/home/ubuntu/app/env

      - name: 🚀 Run deploy script on EC2
        env:
          EC2_HOST: ${{ secrets.EC2_HOST }}
          EC2_USERNAME: ${{ secrets.EC2_USERNAME }}
        run: |
          echo "🧠 Running remote deploy script..."
          ssh -i ~/.ssh/id_rsa -o StrictHostKeyChecking=no $EC2_USERNAME@$EC2_HOST "
            set -e
            cd /home/ubuntu/app
            chmod +x deploy.sh
            ./deploy.sh
          "

      - name: 🧹 Clean up SSH key
        if: always()
        run: rm -f ~/.ssh/id_rsa
