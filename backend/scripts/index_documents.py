import os
import glob
import logging
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import AzureSearch
from pathlib import Path

load_dotenv()

logging.basicConfig(
level=logging.INFO,
format="%(asctime)s - %(levelname)s - %(message)s"
)

logger=logging.getLogger("indexer")


def index_documents():
    """
Reads the PDFs, chunks them, and uploads them to Azure AI Search for the rulebase
"""

    current_dir = Path(__file__).resolve().parent
    data_folder = current_dir.parent / "data"

    logger.info("=" * 60)
    logger.info("Environment Configuration Check:")
    logger.info(f"OPENAI_API_KEY: {'SET' if os.getenv('OPENAI_API_KEY') else 'NOT SET'}")
    logger.info(f"OPENAI_EMBEDDING_MODEL: {os.getenv('OPENAI_EMBEDDING_MODEL', 'text-embedding-3-small')}")
    logger.info(f"SEARCH_ENDPOINT: {os.getenv('AZURE_SEARCH_ENDPOINT')}")
    logger.info(f"SEARCH_INDEX_NAME: {os.getenv('AZURE_SEARCH_INDEX_NAME')}")

    required_vars = [
    "OPENAI_API_KEY",
    "AZURE_SEARCH_ENDPOINT",
    "AZURE_SEARCH_API_KEY",
    "AZURE_SEARCH_INDEX_NAME"
]

    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        logger.error(f"Missing required environment variables: {missing_vars}")
        logger.error("Please check your .env file and ensure all variables are set")
        return

    try:
        logger.info("Initializing OpenAI Embeddings.....")
        embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small"
)
        logger.info("Embeddings model initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize embeddings: {e}")
        logger.error("Please verify your OPENAI_API_KEY and embedding model configuration.")
        return
    vector_store = AzureSearch(
    azure_search_endpoint=os.getenv("AZURE_SEARCH_ENDPOINT"),
    azure_search_key=os.getenv("AZURE_SEARCH_API_KEY"),
    index_name=os.getenv("AZURE_SEARCH_INDEX_NAME"),
    embedding_function=embeddings.embed_query,
)
    pdf_files = glob.glob(os.path.join(data_folder, "*.pdf"))

    if not pdf_files:
        logger.warning(f"No PDFs found in {data_folder}. Please add files.")

    logger.info(
        f"Found {len(pdf_files)} PDFs to process: "
        f"{[os.path.basename(f) for f in pdf_files]}"
    )

    all_splits = []

    for pdf_path in pdf_files:
        try:
            logger.info(f"Loading: {os.path.basename(pdf_path)}......")

            loader = PyPDFLoader(pdf_path)
            raw_docs = loader.load()

            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200
            )

            splits = text_splitter.split_documents(raw_docs)

            for split in splits:
                split.metadata["source"] = os.path.basename(pdf_path)

            all_splits.extend(splits)

            logger.info(f"Split into {len(splits)} chunks.")

        except Exception as e:
            logger.error(f"Failed to process {pdf_path}: {e}")

    if all_splits:
        logger.info(
            f"Uploading {len(all_splits)} chunks to Azure AI Search Index '{os.getenv('AZURE_SEARCH_INDEX_NAME')}'"
        )
        try:
            vector_store.add_documents(documents=all_splits)

            logger.info("=" * 60)
            logger.info("Indexing Complete! Knowledge Base is ready...")
            logger.info(f"Total chunks indexed: {len(all_splits)}")
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"Failed to upload the documents to Azure Search: {e}")
            logger.error("Please check the Azure Search configuration and try again")

    else:
        logger.warning("No documents were processed.")


if __name__ == "__main__":
    index_documents()