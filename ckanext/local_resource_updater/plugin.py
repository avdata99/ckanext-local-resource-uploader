# -*- coding: utf-8 -*-
import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from ckanext.local_resource_updater.resource import LocalResourceStorage


class Local_Resource_UpdaterPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IUploader)

    def get_resource_uploader(self, data_dict):
        # if the resource is in a local path
        # We provide a custom Resource uploader.
        if data_dict.get('upload', '').startswith('/'):
            return LocalResourceStorage(data_dict)
        else:
            return None

    def get_uploader(self, upload_to, old_filename=None):
        # We don't provide misc-file storage (group images for example)
        # Returning None here will use the default Uploader.
        return None
