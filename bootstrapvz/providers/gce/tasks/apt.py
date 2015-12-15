from bootstrapvz.base import Task
from bootstrapvz.common import phases
from bootstrapvz.common.tasks import apt
from bootstrapvz.common.tasks import network
from bootstrapvz.common.tools import log_check_call
import os


class SetPackageRepositories(Task):
	description = 'Adding apt sources'
	phase = phases.preparation
	predecessors = [apt.AddManifestSources, apt.AddBackports]

	@classmethod
	def run(cls, info):
		components = 'main'
		if 'components' in info.manifest.system:
			components = ' '.join(info.manifest.system['components'])
		info.source_lists.add('main', 'deb     http://http.debian.net/debian {system.release} ' + components)
		info.source_lists.add('main', 'deb-src http://http.debian.net/debian {system.release} ' + components)
		info.source_lists.add('backports', 'deb     http://http.debian.net/debian {system.release}-backports ' + components)
		info.source_lists.add('backports', 'deb-src http://http.debian.net/debian {system.release}-backports ' + components)
		info.source_lists.add('google', 'deb http://packages.cloud.google.com/apt google-cloud-compute-legacy-{system.release} main')


class ImportGoogleKey(Task):
	description = 'Adding Google key'
	phase = phases.package_installation
	predecessors = [apt.InstallTrustedKeys]
	successors = [apt.WriteSources]

	@classmethod
	def run(cls, info):
		key_file = os.path.join(info.root, 'google.gpg.key')
		log_check_call(['wget', 'https://packages.cloud.google.com/apt/doc/apt-key.gpg', '-O', key_file])
		log_check_call(['chroot', info.root, 'apt-key', 'add', 'google.gpg.key'])
		os.remove(key_file)


class CleanGoogleRepositoriesAndKeys(Task):
	description = 'Removing Google key and apt source files'
	phase = phases.system_cleaning
	predecessors = [apt.AptClean]
	successors = [network.RemoveDNSInfo]

	@classmethod
	def run(cls, info):
		keys = log_check_call(['chroot', info.root, 'apt-key',
		                       'adv', '--with-colons', '--list-keys'])
		# protect against first lines with debug information,
		# not apt-key output
		key_id = [key.split(':')[4] for key in keys
		          if len(key.split(':')) == 13 and
		          key.split(':')[9].find('@google.com') > 0]
		log_check_call(['chroot', info.root, 'apt-key', 'del', key_id[0]])
		apt_file = os.path.join(info.root, 'etc/apt/sources.list.d/google.list')
		os.remove(apt_file)
		log_check_call(['chroot', info.root, 'apt-get', 'update'])
