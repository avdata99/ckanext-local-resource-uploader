# -*- coding: utf-8 -*-
import datetime
import logging
import magic
import mimetypes
import os

from ckan.lib import munge
from ckan.lib.uploader import get_storage_path, _copy_file
from ckan import logic
from ckan.common import config


log = logging.getLogger(__name__)


class LocalResourceStorage(object):
    def __init__(self, resource):
        log.info('Start a fake upload to copy resource at {}'.format(resource['upload']))

        path = get_storage_path()
        config_mimetype_guess = config.get('ckan.mimetype_guess', 'file_ext')

        if not path:
            self.storage_path = None
            return

        self.storage_path = os.path.join(path, 'resources')
        try:
            os.makedirs(self.storage_path)
        except OSError as e:
            # errno 17 is file already exists
            if e.errno != 17:
                raise
        
        self.filename = None
        self.mimetype = None

        url = resource.get('url')

        upload_path = resource.pop('upload', None)
        resource['upload'] = 'Local File'
        
        upload_field_storage = open(upload_path)
        self.clear = resource.pop('clear_upload', None)

        if config_mimetype_guess == 'file_ext':
            self.mimetype = mimetypes.guess_type(url)[0]

        self.filesize = 0  # bytes

        self.filename = upload_field_storage.filename
        self.filename = munge.munge_filename(self.filename)
        resource['url'] = self.filename
        resource['url_type'] = 'upload'
        resource['last_modified'] = datetime.datetime.utcnow()
        
        self.upload_file = upload_field_storage.file
        self.upload_file.seek(0, os.SEEK_END)
        self.filesize = self.upload_file.tell()
        # go back to the beginning of the file buffer
        self.upload_file.seek(0, os.SEEK_SET)

        # check if the mimetype failed from guessing with the url
        if not self.mimetype and config_mimetype_guess == 'file_ext':
            self.mimetype = mimetypes.guess_type(self.filename)[0]

        if not self.mimetype and config_mimetype_guess == 'file_contents':
            try:
                self.mimetype = magic.from_buffer(self.upload_file.read(), mime=True)
                self.upload_file.seek(0, os.SEEK_SET)
            except IOError as e:
                # Not that important if call above fails
                self.mimetype = None

    def get_directory(self, id):
        directory = os.path.join(self.storage_path, id[0:3], id[3:6])
        return directory

    def get_path(self, id):
        directory = self.get_directory(id)
        filepath = os.path.join(directory, id[6:])
        return filepath

    def upload(self, id, max_size=10):
        '''Actually upload/copy the local file.

        :returns: ``'file uploaded'`` if a new file was successfully uploaded
            (whether it overwrote a previously uploaded file or not),
            ``'file deleted'`` if an existing uploaded file was deleted,
            or ``None`` if nothing changed
        :rtype: ``string`` or ``None``

        '''
        if not self.storage_path:
            return

        # Get directory and filepath on the system
        # where the file for this resource will be stored
        directory = self.get_directory(id)
        filepath = self.get_path(id)

        # If a filename has been provided (a file is being uploaded)
        # we write it to the filepath (and overwrite it if it already
        # exists). This way the uploaded file will always be stored
        # in the same location
        if self.filename:
            try:
                os.makedirs(directory)
            except OSError as e:
                # errno 17 is file already exists
                if e.errno != 17:
                    raise
            tmp_filepath = filepath + '~'
            with open(tmp_filepath, 'wb+') as output_file:
                try:
                    _copy_file(self.upload_file, output_file, max_size)
                except logic.ValidationError:
                    os.remove(tmp_filepath)
                    raise
                finally:
                    self.upload_file.close()
            os.rename(tmp_filepath, filepath)
            return

        # The resource form only sets self.clear (via the input clear_upload)
        # to True when an uploaded file is not replaced by another uploaded
        # file, only if it is replaced by a link to file.
        # If the uploaded file is replaced by a link, we should remove the
        # previously uploaded file to clean up the file system.
        if self.clear:
            try:
                os.remove(filepath)
            except OSError as e:
                pass
