# Sistem Surat IKAMI — v19

Perbaikan nomor surat dan riwayat:

- Menghapus semua riwayat otomatis mereset seluruh nomor urut otomatis.
- Menghapus satu riwayat akan menghitung ulang nomor urut berdasarkan nomor terbesar yang masih tersimpan untuk setiap jenis surat.
- Nomor manual ikut menjadi nomor terakhir untuk jenis surat tersebut. Contoh: memasukkan nomor manual 19 membuat nomor otomatis berikutnya menjadi 20.
- Nomor manual yang lebih kecil dari nomor terakhir tidak menurunkan counter yang sudah lebih tinggi.
- Riwayat sekarang menyimpan kode jenis surat agar sinkronisasi counter lebih akurat. Riwayat lama tanpa kode tetap dicoba dibaca dari format nomor surat.

Jalankan seperti versi sebelumnya.
