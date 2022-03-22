#!/usr/bin/env python3
import argparse
import copy
import logging
import os
import uuid
import subprocess

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def generate_s3_key(project, branch):
    return f'{project}/@{branch}'

class S3Client:

    def __init__(self, url, access_key_id, secret_access_key, region):
        self.url = url
        self.access_key_id = access_key_id
        self.secret_access_key = secret_access_key
        self.region = region
        self.workdir = os.path.join('/tmp', uuid.uuid4().hex)
        os.mkdir(self.workdir)

    def get(self, key):
        the_file = os.path.join(self.workdir, "inclint.txt")
        subprocess.run([
            'aws',
            's3',
            'cp',
            os.path.join(self.url, key, "inclint.txt"),
            the_file,
        ], env=self._env(), check=True)
        
        with open(the_file) as f:
            return f.read()

    def set(self, key, value):
        the_file = os.path.join(self.workdir, "inclint.txt")
        with open(the_file, 'w') as f:
            f.write(str(value))
        subprocess.run([
            'aws',
            's3',
            'cp',
            the_file,
            os.path.join(self.url, key, "inclint.txt"),

        ], env=self._env(), check=True)

    def _env(self):
        base_env = copy.deepcopy(os.environ)
        base_env.update({
            'AWS_ACCESS_KEY_ID': self.access_key_id,
            'AWS_SECRET_ACCESS_KEY': self.secret_access_key,
            'AWS_URL': self.url,
            'AWS_REGION': self.region,
        })
        return base_env


class LinterErrorsFromS3:

    def __init__(self, client, forgiving=True):
        self.client = client
        self.forgiving = forgiving

    def get(self, project, branch):
        try:
            return int(self.client.get(generate_s3_key(project, branch)))
        except Exception as e:
            if self.forgiving:
                logger.error(e)
                logger.warning(
                    f"Could not download amount of errors for project {project}, branch {branch}, assuming it's a lot"
                )
                return 99999
            else:
                raise

    def set(self, project, branch, value):
        self.client.set(generate_s3_key(project, branch), value)


class PrepopulatedLinterErrors:

    def __init__(self, amount_of_errors):
        self.amount_of_errors = int(amount_of_errors)

    def get(self, project, branch):
        return self.amount_of_errors

    def set(self, project, branch):
        raise NotImplementedError()


class CompareSettings:

    def __init__(self, project, branch, threshold):
        self.project = project
        self.branch = branch
        self.threshold = threshold


def compare_linter_errors(
    head_linter_errors, 
    base_linter_errors, 
    settings
):

    head_linter_errors_value = head_linter_errors.get(settings.project, settings.branch)
    if head_linter_errors_value == 0:
        logger.info("No linter errors!")
        return

    base_linter_errors_value = base_linter_errors.get(settings.project, settings.branch)
    if base_linter_errors_value - head_linter_errors_value < 0:
        raise RuntimeError(
            "Head branch contains more linter errors than base branch! "
            f"Head has {head_linter_errors_value}, base has {base_linter_errors_value}"
        )
    
    if base_linter_errors_value - head_linter_errors_value < settings.threshold:
        raise RuntimeError(
            f"Head branch should contain at least {settings.threshold} less linter errors than base branch! "
            f"Head has {head_linter_errors_value}, base has {base_linter_errors_value}"
        )


def normalize_branch(branch):
    prefix = 'refs/heads/'
    return branch[len(prefix):] if branch.startswith(prefix) else branch


ACTION_UPDATE = 'update'
ACTION_COMPARE = 'compare'

if __name__ == "__main__":
    argument_parser = argparse.ArgumentParser(
        description="Allows comparing linter errors between branches and updating linter errors in S3"
    )
    argument_parser.add_argument(
        '--action', required=True,
        help=f'Action, one of: {ACTION_UPDATE}, {ACTION_COMPARE}',
    )
    
    # Linter errors
    argument_parser.add_argument(
        '--head-linter-errors', required=True,
        help='Head linter errors, should be numeric'
    )
    argument_parser.add_argument(
        '--threshold', default=5,
        help='Threshhold - this much linters must be fixed with every PR'
    )

    # AWS
    argument_parser.add_argument(
        '--aws-url', required=False, default='s3://github-code-coverage/365days/inclint/',
        help='AWS url (for example s3://github-code-coverage/365days/inclint/) '
    )
    argument_parser.add_argument(
        '--aws-aki', required=True,
        help='AWS Access Key ID'
    )
    argument_parser.add_argument(
        '--aws-sac', required=True,
        help='AWS Secret Access Key'
    )
    argument_parser.add_argument(
        '--aws-region', required=False, default='eu-central-1',
        help='AWS Region'
    )

    # Target
    argument_parser.add_argument(
        '--project', required=True,
        help='AWS Region'
    )
    argument_parser.add_argument(
        '--branch', required=True,
        help='AWS Region'
    )

    args = argument_parser.parse_args()

    linter_errors_from_s3 = LinterErrorsFromS3(S3Client(args.aws_url, args.aws_aki, args.aws_sac, args.aws_region))
    if args.action == ACTION_COMPARE:
        compare_linter_errors(
            PrepopulatedLinterErrors(args.head_linter_errors),
            linter_errors_from_s3,
            CompareSettings(
                args.project,
                normalize_branch(args.branch),
                int(args.threshold)
            )
        )
    elif args.action == ACTION_UPDATE:
        linter_errors_from_s3.set(
            args.project,
            normalize_branch(args.branch),
            args.head_linter_errors
        )
    else:
        raise RuntimeError("Invalid action")
