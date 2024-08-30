from langchain_community.document_loaders.recursive_url_loader import RecursiveUrlLoader
from quivr_api.models.files import File

from .common import process_file


def process_recursive_url(
    file: File, brain_id, original_file_name, integration=None, integration_link=None
):
    return process_file(
        file=file,
        loader_class=RecursiveUrlLoader,
        brain_id=brain_id,
        original_file_name=original_file_name,
        integration=integration,
        integration_link=integration_link,
    )
