#!/usr/bin/env python3
import argparse
import copy
import logging
import os
import re
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
        the_file = os.path.join(self.workdir, "coverage.txt")
        subprocess.run([
            'aws',
            's3',
            'cp',
            os.path.join(self.url, key, "coverage.txt"),
            the_file,
        ], env=self._env(), check=True)

        with open(the_file) as f:
            return f.read()

    def set(self, key, value):
        the_file = os.path.join(self.workdir, "coverage.txt")
        with open(the_file, 'w') as f:
            f.write(str(value))
        subprocess.run([
            'aws',
            's3',
            'cp',
            the_file,
            os.path.join(self.url, key, "coverage.txt"),

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


class CoverageFromS3:

    def __init__(self, client, forgiving=True):
        self.client = client
        self.forgiving = forgiving

    def get(self, project, branch):
        try:
            return float(self.client.get(generate_s3_key(project, branch)))
        except Exception as e:
            if self.forgiving:
                logger.error(e)
                logger.warning(
                    f"Could not download coverage for project {project}, branch {branch}, assuming it's 0"
                )
                return 0
            else:
                raise

    def set(self, project, branch, value):
        self.client.set(generate_s3_key(project, branch), value)


class PrepopulatedCoverage:

    def __init__(self, coverage):
        self.coverage = float(coverage)

    def get(self, project, branch):
        return self.coverage

    def set(self, project, branch):
        raise NotImplementedError()


class CompareSettings:

    def __init__(self, project, branch, threshold, skip_on_hotfix):
        self.project = project
        self.branch = branch
        self.threshold = threshold
        self.skip_on_hotfix = skip_on_hotfix


def is_hotfix(branch):
    return 'hotfix' in branch.lower()


def compare_coverage(
    head_coverage,
    base_coverage,
    settings,
    current_branch
):
    if settings.skip_on_hotfix and is_hotfix(current_branch):
        logger.info(
            f'{settings.branch} is a hotfix branch. Skipping coverage comparison.')
        return

    head_coverage_value = head_coverage.get(settings.project, settings.branch)
    if head_coverage_value > settings.threshold:
        logger.info(
            f'HEAD coverage ({head_coverage_value}) is greater than theshold ({settings.threshold}), no need to compare with base branch'
        )
        return

    base_coverage_value = base_coverage.get(settings.project, settings.branch)
    if base_coverage_value >= head_coverage_value:
        raise RuntimeError(
            f'Head coverage ({head_coverage_value}) should be greater than base coverage ({base_coverage_value}), failing the build'
        )
    logger.info(
        f'Head coverage ({head_coverage_value}) should be greater than base coverage ({base_coverage_value}) - OK!'
    )


def normalize_branch(branch):
    prefix = 'refs/heads/'
    return branch[len(prefix):] if branch.startswith(prefix) else branch


ACTION_UPDATE = 'update'
ACTION_COMPARE = 'compare'

if __name__ == "__main__":
    argument_parser = argparse.ArgumentParser(
        description="Allows comparing coverage between branches and updating the coverage in S3"
    )
    argument_parser.add_argument(
        '--action', required=True,
        help=f'Action, one of: {ACTION_UPDATE}, {ACTION_COMPARE}',
    )

    # Coverage
    argument_parser.add_argument(
        '--current-branch', required=True,
        help='Current branch. Should be passed from workflow.'
    )
    argument_parser.add_argument(
        '--head-coverage', required=True,
        help='Head coverage, should be numeric'
    )
    argument_parser.add_argument(
        '--threshold', default=80,
        help='Threshhold at which comparison results don\'t matter, should be numeric'
    )
    argument_parser.add_argument(
        '--skip-on-hotfix', action=argparse.BooleanOptionalAction, default=True
    )

    # AWS
    argument_parser.add_argument(
        '--aws-url', required=False, default='s3://github-code-coverage/365days/coverage/',
        help='AWS url (for example s3://github-code-coverage/365days/coverage/) '
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
        help='Github ref or branch name'
    )

    args = argument_parser.parse_args()

    coverage_from_s3 = CoverageFromS3(
        S3Client(args.aws_url, args.aws_aki, args.aws_sac, args.aws_region))
    if args.action == ACTION_COMPARE:
        compare_coverage(
            PrepopulatedCoverage(args.head_coverage),
            coverage_from_s3,
            CompareSettings(
                args.project,
                normalize_branch(args.branch),
                float(args.threshold),
                args.skip_on_hotfix
            ),
            normalize_branch(args.current_branch)
        )
    elif args.action == ACTION_UPDATE:
        coverage_from_s3.set(
            args.project,
            normalize_branch(args.branch),
            args.head_coverage
        )
    else:
        raise RuntimeError("Invalid action")
