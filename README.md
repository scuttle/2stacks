# 2stacks
Tools for backing up scp-wiki.net.

## Requirements
* A [SCUTTLE](https://github.com/scuttle/scuttle) installation with 'write-programmatically' access. (Currently limited to User ID 1)
* A Wikidot API key.

Please note these are meant for use in AWS Lambda, receiving a message from Amazon SQS, and are formatted for that purpose.

This repo is primarily for version control and rollback-ability.

2stacks is built alongside [SCUTTLE](https://github.com/scuttle/scuttle) and is built for that platform first. If you can make these lambdas work for your project, great.