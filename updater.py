#!/bin/python3
import yaml
import io
import requests
import hashlib
from git import Repo
import argparse
import os.path
import sys
import tempfile

parser = argparse.ArgumentParser(description='Update Conan Center Index')
parser.add_argument(
    '--fork', help='The fork of the Conan Center Index', required=True)
parser.add_argument('--version', help='The version to add', required=True)
parser.add_argument('--recipe', help='The recipe to update', required=True)
parser.add_argument('--access-token', help='The personal access token to use to push the changes', required=True)
parser.add_argument('--user', help='The user name to use to push the changes', required=True)
parser.add_argument(
    '--zipball', help='The URL of the archive to add', required=True)
parser.add_argument('--dryrun', help='Dry run, do not push',
                    action='store_true')


args = parser.parse_args()
target_dir_ = tempfile.mkdtemp()

repository_url = "https://{}:{}@github.com/{}.git".format(args.user, args.access_token, args.fork)


repo = Repo.clone_from(repository_url, target_dir_)
branch_name = "{}/{}".format(args.recipe, args.version)
branch = repo.create_head(branch_name)
branch.checkout()

recipe_dir = os.path.join(target_dir_, "recipes", args.recipe)
if not os.path.exists(recipe_dir):
    print("Recipe not found")
    sys.exit(1)


with open(os.path.join(recipe_dir, "configX.yml"), 'r') as stream:
    data_loaded = yaml.safe_load(stream)

new_version = dict()
data_loaded["versions"][args.version] = {'folder': 'all'}

with io.open(os.path.join(recipe_dir, 'config.yml'), 'w', encoding='utf8') as outfile:
    yaml.dump(data_loaded, outfile,
              default_flow_style=False, allow_unicode=True)

r = requests.get(args.zipball, allow_redirects=True)
hash = hashlib.sha256(r.content).hexdigest()

with open(os.path.join(recipe_dir, "all", "conandata.yml"), 'r') as stream:
    conandata = yaml.safe_load(stream)

conandata["sources"][args.version] = {
    'url': args.zipball, 'sha256': hash}

with io.open(os.path.join(recipe_dir, 'conandata.yml'), 'w', encoding='utf8') as outfile:
    yaml.dump(conandata, outfile,
              default_flow_style=False, allow_unicode=True)

repo.index.add(os.path.join(recipe_dir, "config.yml"))
repo.index.add(os.path.join(recipe_dir, "conandata.yml"))
repo.index.commit("Update {} to version {}".format(args.recipe, args.version))
if not args.dryrun:
    repo.remotes.origin.push(refspec="{}:{}".format(branch_name, branch_name))
else:
    print("Dry run, not pushing")
