#!/usr/bin/env python3
import argparse
import copy
import logging
import os
import sys
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
        print(' '.join([
            'aws',
            's3',
            'cp',
            os.path.join(self.url, key, "coverage.txt"),
            the_file,
        ]))
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

        print(' '.join([
            'aws',
            's3',
            'cp',
            the_file,
            os.path.join(self.url, key, "coverage.txt"),

        ]))
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

    def __init__(self, project, branch, threshold):
        self.project = project
        self.branch = branch
        self.threshold = threshold


def compare_coverage(
    head_coverage, 
    base_coverage, 
    settings
):

    head_coverage_value = head_coverage.get(settings.project, settings.branch)
    if head_coverage_value > settings.threshold:
        logger.info(
            f'HEAD coverage ({head_coverage_value}) is greater than theshold ({settings.threshold}), no need to compare with base branch'
        )
        return

    base_coverage_value = base_coverage.get(settings.project, settings.branch)
    if base_coverage_value > head_coverage_value:
        raise RuntimeError(
            f'Base coverage ({base_coverage_value}) is greater than HEAD coverage ({head_coverage_value}), failing the build'
        )


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
        '--head-coverage', required=True,
        help='Head coverage, should be numeric'
    )
    argument_parser.add_argument(
        '--threshold', default=80,
        help='Threshhold at which comparison results don\'t matter, should be numeric'
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

    argument_parser.add_argument(
        '--project', required=True,
        help='AWS Region'
    )

    argument_parser.add_argument(
        '--branch', required=True,
        help='AWS Region'
    )

    args = argument_parser.parse_args()

    coverage_from_s3 = CoverageFromS3(S3Client(args.aws_url, args.aws_aki, args.aws_sac, args.aws_region))

    if args.action == ACTION_COMPARE:
        compare_coverage(
            PrepopulatedCoverage(args.head_coverage),
            coverage_from_s3,
            CompareSettings(
                args.project,
                args.branch,
                float(args.threshold)
            )
        )
    elif args.action == ACTION_UPDATE:
        coverage_from_s3.set(
            args.project,
            args.branch,
            args.head_coverage
        )
    else:
        coverage_from_s3.set("PiwikPRO/barman", "master", 11)
        raise RuntimeError("Invalid action")
