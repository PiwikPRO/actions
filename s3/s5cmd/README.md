# S3 Fast Transfer Actions
This GitHub Actions provides a high-performance alternative for uploading and downloading objects to/from Amazon S3 using s5cmd.

## 🚀 Why use `s5cmd`?
While the standard AWS CLI is the reliable "go-to" for most S3 operations, it often becomes a bottleneck when dealing with a large volume of small files.
**s5cmd** is a faster, parallelized alternative written in Go. 
The performance gains are significant when uploading our standard Allure report:
* **AWS CLI:** ~7 minutes
* **`s5cmd`:** ~1 minute

## ⚖️ Why is this a separate action?
This as a separate action rather than replacing our existing AWS CLI-based workflow for several reasons:
- **Stability:** A previous implementation using `s5cmd` was unstable due to proxy timeouts. This version needs to be monitored under various network conditions.
- **Maturity:** We need to verify that this current implementation does not have any unforeseen drawbacks before making it the default.
- **Rollback Safety:** Keeping it separate allows teams to revert to the proven AWS CLI solution instantly if issues arise.

---

## 🛠 Usage
The behavior and inputs are designed to be a drop-in replacement for the standard `PiwikPRO/actions/s3/upload`.

### Upload
```yaml
- name: Upload to S3
  uses: PiwikPRO/actions/s3/s5cmd/upload@master
  with:
    aws-access-key-id: ${{ inputs.aws-access-key-id }}
    aws-secret-access-key: ${{ inputs.aws-secret-access-key }}
    aws-http-proxy: ${{ inputs.aws-http-proxy }}
    aws-https-proxy: ${{ inputs.aws-https-proxy }}
    aws-bucket: piwikpro-artifactory
    aws-region: eu-central-1
    src-path: artifacts/
    dst-path: ${{ github.repository }}/@${{ github.ref_name }}/artifacts/
    echo-destination-index-html: true
```

### Download
The download action includes an additional `ignore-missing` flag, which prevents the step from failing if no files are found at the source path.
```yaml
- name: Download from S3
  uses: PiwikPRO/actions/s3/s5cmd/download@master
  with:
    aws-access-key-id: ${{ inputs.aws-access-key-id }}
    aws-secret-access-key: ${{ inputs.aws-secret-access-key }}
    aws-http-proxy: ${{ inputs.aws-http-proxy }}
    aws-https-proxy: ${{ inputs.aws-https-proxy }}
    aws-bucket: piwikpro-artifactory
    aws-region: eu-central-1
    src-path: ${{ github.repository }}/@${{ github.ref_name }}/artifacts/
    dst-path: dest-path/
    ignore-missing: true
```