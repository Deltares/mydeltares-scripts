<h1>MyDeltares pentaho scripts</h1>

These Pentaho scripts contain a number of ETL scripts that allowyou to extract user data from different Deltares user repositories:
- DSD MongoDB
- OSS community repository

The extracted data can then be filtered to remove any unwanted or invalid user data. 
The extracted and filtered data can be uploaded into the new MyDeltares user repository. 


<h2>DSD MongoDB scripts</h2>
Export users from the DSD mongodb and filter out any unwanted users by email address:

    Place all unwanted email addresses in file: liferay/input/unwanted_emails.csv

    run batch: mongodb/export and filter emails.kjb

    batch expects input configuration: ../../config/mongodb.properties
    mongo_server=
    mongo_port=
    mongo_database=
    mongo_user=
    mongo_pw=

<h2>OSS Community portal scripts</h2>
Export users from Liferay and filter out any unwanted users by email address:

    Go to Liferay console and under users export to csv. Place export file in file: liferay/input/liferay_eported_users.csv

    Place all unwanted email addresses in file: liferay/input/unwanted_emails.csv

    run batch: liferay/filter emails.kjb

    batch expects input configuration: ../../config/liferay.properties
    liferay_url=
    client_id=
    client_secret=
    companyid=
    scope=

<h2>MyDeltares scripts</h2>
Merge output from Liferay and from MongoDB to get single list of users. (liferay values overrule mongodb values):

    Place liferay output in file: merge_valid_users/input/liferay_valid_users.csv
    Place mongodb output in file: merge_valid_users/input/dsd_valid_users.csv
    run batch: merge_valid_users/merge_users.kjb

Upload exported, filtered and merged users to Keycloak:

    Place merged output in file: keycloak/input/merged_users.csv

    run batch:keycloak/import_users.kjb

    batch expects input configuration: ../../config/keycloak.properties
    keycloak_url=
    client_id=
    client_secret=
    scope=
