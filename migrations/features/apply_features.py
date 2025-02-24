import argparse
import os
from typing import Optional

from snowflake.ml.feature_store import CreationMode, FeatureStore
from snowflake.snowpark import Session

from mlplatform.features.entities import entities
from mlplatform.features.features import feature_views
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend


def apply_feature_changes(session: Session, mode: Optional[str] = "prod"):

    fs = FeatureStore(
        session=session,
        database=session.get_current_database(),
        name=session.get_current_schema(),
        default_warehouse=session.get_current_warehouse(),
        creation_mode=CreationMode.CREATE_IF_NOT_EXIST,
    )

    for entity in entities:
        fs.register_entity(entity) # Incrementally add new entities (built in)

    for feature_view in feature_views(session):
        if mode == "test": # Skip creation of dynamic tables
            feature_view['feature_view']._refresh_freq=None
        fs.register_feature_view(**feature_view) # Incrementally add new feature views (built in)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Apply feature changes to Snowflake feature store.")
    parser.add_argument("--mode", choices=["test"], required=False, help="Specify if running in testing mode.")
    args = parser.parse_args()
    
    passphrase = os.environ.get("SNOWFLAKE_CONNECTIONS_SNOWCONNECTION_PASSPHRASE")
    private_key = os.environ.get("SNOWFLAKE_CONNECTIONS_SNOWCONNECTION_RSAKEY")
    if private_key is None:
        raise ValueError("No private key found in environment variables")
    
    # Convert the key to bytes
    private_key_bytes = private_key.encode('utf-8')
    
    private_key_obj = serialization.load_pem_private_key(
            private_key_bytes,
            password=passphrase.encode() if passphrase else None,
            backend=default_backend()
        )
    
    connection_parameters = {
        "ACCOUNT": os.getenv("SNOWFLAKE_CONNECTIONS_SNOWCONNECTION_ACCOUNT"),
        "USER": os.getenv("SNOWFLAKE_CONNECTIONS_SNOWCONNECTION_USER"),
        "PASSWORD": os.getenv("SNOWFLAKE_CONNECTIONS_SNOWCONNECTION_PASSWORD"),
        "ROLE": os.getenv("SNOWFLAKE_CONNECTIONS_SNOWCONNECTION_ROLE"),
        "WAREHOUSE": os.getenv("SNOWFLAKE_CONNECTIONS_SNOWCONNECTION_WAREHOUSE"),
        "DATABASE": os.getenv("SNOWFLAKE_DATABASE"),
        "SCHEMA": os.getenv("SNOWFLAKE_SCHEMA"),
        "private_key": private_key_obj,
    }

    session = Session.builder.configs(connection_parameters).create()
    apply_feature_changes(session, args.mode)
