#!/bin/bash
set -e

# Configuration
API_URL="http://localhost:8001/api/v1"
TEST_EMAIL="e2e_curl_$(date +%s)@test.com"
TEST_PASS="testpass123"
PDF_FILE="scripts/test_document.pdf"

echo "[*] Creating test PDF..."
python3 -c "
import fitz
doc = fitz.open()
page = doc.new_page()
page.insert_text((50, 50), 'The secret code for the document insight platform is 42-ALPHA-ZULU.')
doc.save('$PDF_FILE')
doc.close()
"

echo "[*] Registering user: $TEST_EMAIL"
curl -s -X POST "$API_URL/auth/register" \
     -H "Content-Type: application/json" \
     -d "{\"email\": \"$TEST_EMAIL\", \"password\": \"$TEST_PASS\", \"full_name\": \"E2E Curl User\"}"

echo -e "\n[*] Logging in..."
LOGIN_JSON=$(curl -s -X POST "$API_URL/auth/login" \
     -F "username=$TEST_EMAIL" \
     -F "password=$TEST_PASS")

TOKEN=$(echo $LOGIN_JSON | grep -oP '"access_token":"\K[^"]+')
if [ -z "$TOKEN" ]; then
    echo "[ERROR] Login failed!"
    echo $LOGIN_JSON
    exit 1
fi
echo "[*] Token received: ${TOKEN:0:10}..."

echo "[*] Uploading document..."
UPLOAD_JSON=$(curl -s -X POST "$API_URL/upload_documents/" \
     -H "Authorization: Bearer $TOKEN" \
     -F "files=@$PDF_FILE")

DOC_ID=$(echo $UPLOAD_JSON | grep -oP '"task_id":"\K[^"]+')
echo "[*] Uploaded! Document ID: $DOC_ID"

echo "[*] Waiting 10 seconds for background vectorization..."
sleep 10

echo "[*] Performing RAG Query..."
QUERY_JSON=$(curl -s -X POST "$API_URL/query/ask" \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d "{\"question\": \"What is the secret code?\"}")

echo "--------------------------------------------------"
echo "RAG ANSWER:"
echo $QUERY_JSON | grep -oP '"answer":"\K[^"]+'
echo "--------------------------------------------------"

# Optional Cleanup
# echo "[*] Cleaning up doc..."
# curl -s -X DELETE "$API_URL/documents/$DOC_ID" -H "Authorization: Bearer $TOKEN"

echo "[*] E2E Curl Test Finished Successfully!"
rm $PDF_FILE
