# `airflow-cloud-run`: Airflow's pipeline to orchestrate the submitted cloud run job in MongoDB collection

| Context     | Description |
| ----------- | ----------- |
| What        | Setup data pipeline workflow untuk melakukan trigger cloud run job dari data yang di queue di MongoDB collection   |
| Who         | Siapapun yang ingin melakukan deployment atau yang ingin mencoba ini di lokal        |
| When        | Ketika melakukan deploy dari awal atau re-deployment        |
| Where       | Ubuntu 18.04+ w/ Docker and Docker Compose        |
| Why         | Agar job yang disubmit ke MongoDB collection dapat dijalankan dan dikontrol secara baik oleh sebuah workflow orchestrator (yang dalam hal ini Airflow)      |
| How         | Read more . . .        |

## 📝 Repository Structure

Berikut adalah struktur dari repositori `fac_project_coin_data_engineering`

```bash
fac_project_coin_data_engineering/          # root directory repository
  coin_calculation_airflow/                 # direktori utama dari fitur baru, yaitu melakukan housekeeping trigger cloud run dari kalkulasi project coin
    dags/                                   # tempat file definisi DAG (Directed Acyclic Graph) diletakkan
      lnk/                                  # tempat dari modul yang akan digunakan pada DAG. lnk memiliki scope paling atas 
        common/                             # common module yang akan digunakan pada project ini
          __init__.py                       # python __init__.py file
          sql.py                            # disini terdapat definisi task yang digunakan untuk melakukan trigger cloud run endpoint
        __init__.py                         # python __init__.py file. namun terdapat juga konfigurasi parameter default dari sebuah task dan dag yang akan didefinisikan
      trigger_calculation_dag.py            # file untuk mendefinisikan dag untuk melakukan trigger ke cloud run
    logs/                                   # tempat airflow logs disimpan
    plugins/                                # berguna jika ingin menambahkan plugin baru untuk airflow
    postgres_metadata_db/                   # direktori yang disiapkan untuk menyimpan data pada postgres airflow metadata db
    secret/                                 # tempat menyimpan file credentials  
      connections.yaml.example              # contoh file `connections.yaml`
      variables.json.example                # contoh file `variables.json`
    .env.example                            # environment variable ketika melakukan deployment ke airflow
    dependencies.txt                        # pip dependency yang dibutukan pada dag ini
    docker-compose.yml                      # definisi tiap service yang akan di deploy dalam bentuk docker
    Dockerfile                              # file definisi custom atau extensi image dari airflow
    README.md                               # file ini
```

## 🎯 Pre-requisites

- Git
- Docker installed in VM
- Docker Compose v1.27.4
- Coffee ☕

## 👨‍💻 Set-up

1. Clone repository ini ke dalam target VM yang akan dideploy

  ```bash
    git clone https://gitlab.com/PT.LautanNaturalKrimerindo/fac_project_coin_data_engineering.git
    cd fac_project_coin_data_engineering/coin_calculation_airflow
  ```

2. Cek terlebih dahulu UID dari user yang sedang login di VM, kemudian simpan nilai UID dari user yang sedang login. Gunakan perintah berikut:

  ```bash
    id -u
    # sample output: 1001
  ```

3. Copy file template `.env-example` ke `.env`:

  ```bash
    cp .env-example .env
  ```

4. Buka file `.env`. Isi beberapa properti berikut

  ```bash
    # Airflow Webserver and DB creds
    _AIRFLOW_POSTGRES_USERNAME=your_airflow_pg_user # Username dari untuk akses ke airflow metadata db
    _AIRFLOW_POSTGRES_PASSWORD=your_airflow_pg_pass # Username dari untuk akses ke airflow metadata db

    _AIRFLOW_POSTGRES_EXTERNAL_PORT=55432 # Isi value ini agar airflow metadata db dapat diakses diluar docker dan vm
    _AIRFLOW_WWW_USER_USERNAME=your_airflow_user # Username untuk login ke airflow webserver
    _AIRFLOW_WWW_USER_PASSWORD=your_airflow_pass # Password untuk login ke airflow webserver

    # Webserver Access from Outside
    AIRFLOW_WEBSERVER_PORT=58080 # Isi value ini agar airflow web dapat diakses diluar docker dan vm 
    AIRFLOW_WEBSERVER_BASE_URL='http://localhost:${AIRFLOW_WEBSERVER_PORT}' # ganti localhost dengan alamat ip dari vm ketika diakses di luar

    # Mail Config (Isi bagian berikut agar airflow dapat menggunakan mail service)
    AIRFLOW_SMTP_HOST='<smtp_server_host>'
    AIRFLOW_SMTP_PORT='<smtp_server_port>'
    AIRFLOW_SMTP_USER='<user_email>'
    AIRFLOW_SMTP_PASSWORD='<pass_of_user_email>'
    AIRFLOW_SMTP_MAIL_FROM='<user_email>'

    AIRFLOW_UID=1001 # Isi dengan nilai yang ada pada perintah `id -u`
    AIRFLOW_GID=0
  ```

5. Copy file template koneksi dari `secret/connections.yaml.example` ke `secret/connections.yaml`

  ```bash
    cp secret/connections.yaml.example secret/connections.yaml
  ```

6. Buka file `secret/connections.yaml`. Isi beberapa properti berikut

  ```yaml
    coin_mongo_db:
        conn_type: mongo
        description: ''
        extra: '{"authSource": "admin"}'
        host: <your_mongo_db_host>
        login: <your_mongo_db_user>
        password: <your_mongo_db_pass>
        port: null
        schema: <your_mongodb_schema> 
  ```  

7. Copy file template koneksi dari `secret/variables.json.example` ke `secret/variables.json`

  ```bash
    cp secret/variables.json.example secret/variables.json
  ```

8. Buka file `secret/variables.json`. Pastikan anda mengisi `START_DATE` untuk menentukan starting point data pada tanggal berapa yang akan di ekspor (karena pipeline ini akan berjalan secara parsial mengikuti jadwal scheduler). Isi beberapa properti berikut:

  ```json
    {
      "ENVIRONMENT_PREFIX": "dev", # isi dengan prod atau dev sesuai dengan environment tipe dari VM
      "START_DATE": "2022-01-01 00:00:00", # Format: YYYY-mm-dd HH:MM:SS
      "END_DATE": null, # Opsional: Biarkan null jika pipeline akan dijalankan secara terus menerus / continue. Format sama seperti START_DATE
      "START_END_DATE_TIMEZONE": "Asia/Jakarta", # Gunakan format TZ database name standar dari IANA
      "COIN_INVOKE_URL": "https://you-cloud-run-app.run.app/submit_job", # URL untuk menjalankan job coin
      "JOBS_COLLECTION": "cloud_run_jobs", # Nama collection yang digunakan untuk menyimpan data scheduled job di MongoDB
    }
  ```

9. Setelah semua variabel terisi. Jalankan perintah berikut untuk melakukan deployment menggunakan docker-compose:

  ```bash
    docker-compose up -d # gunakan sudo jika memerlukan superuser/root permission
  ```

10. Masuk ke airflow web pada browser dengan menggunakan alamat yang sudah di *set* pada .env variable *AIRFLOW_WEBSERVER_BASE_URL*. Login dengan menggunakan alamat yang sudah di set di file `.env`

  ![Airflow | Login](./.md-files/login.png)

11. Berikut adalah tampilan dari deployment yang berhasil. Secara default DAGs di-disable ketika pertama kali di-deploy. Pengguna perlu mengaktifkan DAG terlebih dahulu dengan menekan tombol yang ada di samping kiri DAG.


  ![Airflow | Home](./.md-files/home.png)


12. Masuk ke DAG `airflow-sensor-mongodb`. Ketika DAG pertama kali di aktifkan, maka Airflow akan menjalankan proses ekspor data mulai dari `START_DATE` yang telah diisi pada environment variable. Proses ini disebut sebagai ***catchup***. Proses tersebut akan melakukan query ke jobs collection yang ada di MongoDB sesuai dengan interval scheduler yang telah didefinisikan sebelumnya (lihat pada `date_interval_start` dan `date_interval_end`). Job yang diambil disini adalah job pada MongoDB masih berstatus `scheduled`. 

    Task `mongo-sense-collection` disini akan melakukan mapping ke task `trigger_cloud_run_dag` berdasarkan jumlah data yang di-query dari source collection MongoDB. Dalam screenshot diatas, terlihat bahwa terdapat 4 buah data dari MongoDB dalam data interval `2022-05-07 15:00` s/d `2022-05-07 15:05` yang masing-masingnya akan melakukan trigger terhadap sebuah DAG dengan id: **trigger-cloud-run-app**.

  ![Airflow | Catchup Demo Run](./.md-files/demo-run.png)

  Keterangan Warna
  - **Hijau tua**: DAG berhasil dan ada sebuah job yang siap untuk dijalankan di cloud run pada interval tersebut
  - **Merah muda**: DAG berhasil, namun tidak ada job yang siap untuk dijalankan pada interval tersebut
  - **Hijau muda**: DAG data sedang berjalan
  - **Kuning**: DAG gagal dan Airflow *scheduler* mencoba mengulangi proses tersebut (dengan memasukkan ke dalam antrian lagi).
  - **Merah**: DAG gagal. Ada error pada script

13. Kembali ke Home dan masuk ke DAG `trigger-cloud-run-app-coin`. DAG ini tidak memiliki scheduler dan hanya akan dijalankan oleh trigger pada DAG `airflow-sensor-mongodb`. Task akan di-trigger sesuai dengan urutan data tersebut ketika diterima oleh sensor pada DAG sebelumnya (lebih tepatnya berdasarkan field `created_at`).

 ![Airflow | Trigger Task By Sequence](./.md-files/trigger.png)