# Allure history action
Same as `PiwikPRO/actions/allure/history` but uses faster `s5cmd`.

## ⚖️ Why is this a separate action?
This as a separate action rather than replacing our existing workflow because previous implementation was unstable due to proxy timeouts.
We need to verify that this current implementation does not have any issues before making it the default.

---

## 🛠 Usage
```yaml
- name: Generate S3 paths
  uses: PiwikPRO/actions/allure/s3_path@master
  with:
    environment: ${{ inputs.environment }} # usually it’s just inputs.environment or matrix.environment
    team: 'qa-team'  # required field. cia/mit etc.
    matrix_block: ${{ matrix.testblock }} # optional field. Use if the matrix strategy is used.
    retention: '30days'  # optional field. Default value is 30days

- name: Report generating
  uses: PiwikPRO/actions/allure/history_fast@master
  with:
    aws-access-key-id: ${{ secrets.ARTIFACTORY_S3_ACCESS_KEY_ID }}
    aws-secret-access-key: ${{ secrets.ARTIFACTORY_S3_SECRET_ACCESS_KEY }}
    aws-http-proxy: ${{ secrets.FORWARD_PROXY_HTTP }}
    aws-https-proxy: ${{ secrets.FORWARD_PROXY_HTTPS }}
    environment:  # usually it’s just inputs.environment or matrix.environment
    team: 'qa-team' # required field. cia/mit etc.
    enable-history: 'true'  # optional field. Default value is false. 
    retention: '60days' # optional field. Default value is 30days
```