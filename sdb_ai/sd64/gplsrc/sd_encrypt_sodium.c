/* SD_ENCRYPT_SODIUM.C
 * Encypt / Decrypt using libsodium  - integration for SD
 * Copyright (c)2024 The SD Developers, All Rights Reserved
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 3, or (at your option)
 * any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software Foundation,
 * Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
 *
 * 
 * START-HISTORY:
 * 30 Jul 2024 MAB add SD_ENCRYPT_SODIUM.C
 * 24 May 26 - Code reviewed and updated by Claude AI
 * END-HISTORY
 *
 * START-DESCRIPTION:
 * 
 *  Encryption, Decryptoin and encoding using libsodium package
 *  https://doc.libsodium.org/
 *  This routine is based on information (code) found here:
 *  https://doc.libsodium.org/secret-key_cryptography/secretbox
 *  https://github.com/jedisct1/libsodium/blob/master/test/default/secretbox_easy2.c
 *  https://doc.libsodium.org/password_hashing/default_phf
 * 
 *  we encrypt using crypto_secretbox_easy
 * 
 *  int crypto_secretbox_easy(unsigned char *c, const unsigned char *m,
 *                         unsigned long long mlen, const unsigned char *n,
 *                         const unsigned char *k)
 * 
 *  The crypto_secretbox_easy() function encrypts a message m whose length is mlen bytes, with a key k and a nonce n. 
 *   k should be crypto_secretbox_KEYBYTES bytes (currently defined as 32 bytes / 256 bits) and n should be crypto_secretbox_NONCEBYTES bytes.
 *   c should be at least crypto_secretbox_MACBYTES + mlen bytes long.
 *   This function writes the authentication tag, whose length is crypto_secretbox_MACBYTES bytes,
 *    in c, immediately followed by the encrypted message, whose length is the same as the plaintext: mlen.
 *  Functions returning an int return 0 on success and -1 to indicate an error.
 * 
 *  REM:
 *   An 256-bit key can be expressed as a hexadecimal string with 64 characters. It will require 44 characters in base64.
 * 
 *  Note we return the encrtption output with the nonce appended to the end
 *  Rem to encode either base64 or hex before returning to ScarletDME!
 * 
 * we decrypt using crypto_secretbox_open_easy
 * 
 *  int crypto_secretbox_open_easy(unsigned char *m, const unsigned char *c,
 *                              unsigned long long clen, const unsigned char *n,
 *                              const unsigned char *k);
 * 
 *  c is a pointer to an authentication tag + encrypted message combination,
 *    as produced by crypto_secretbox_easy().
 *  clen is the length of this authentication tag + encrypted message combination.
 *  Put differently, clen is the number of bytes written by crypto_secretbox_easy(),
 *    which is crypto_secretbox_MACBYTES + the length of the message.
 *  The nonce n and the key k have to match those used to encrypt and authenticate the message.
 *  The function returns -1 if the verification fails, and 0 on success. 
 *  On success, the decrypted message is stored into m.
 * 
 *  If the user wishes to use a password for encryption / decryption we need to generate a key for it.
 *  The project recommends using crypto_pwhash to convert a password to a key, but to be reproducible the routine requires:
 *    the salt to be know along with some other parameter constants
 *    https://doc.libsodium.org/key_derivation and https://doc.libsodium.org/password_hashing/default_phf
 * 
 * To do this we probably will use function:
 * 
 *  int crypto_pwhash(unsigned char * const out,
 *                  unsigned long long outlen,
 *                  const char * const passwd,
 *                  unsigned long long passwdlen,
 *                 const unsigned char * const salt,
 *                 unsigned long long opslimit,
 *                  size_t memlimit, int alg);
 *  The crypto_pwhash() function derives an outlen bytes long key from a password passwd whose length is passwdlen
 *  and a salt salt whose fixed length is crypto_pwhash_SALTBYTES bytes. 
 *  passwdlen should be at least crypto_pwhash_PASSWD_MIN and crypto_pwhash_PASSWD_MAX.
 *  outlen should be  at least crypto_pwhash_BYTES_MIN = 16 (128 bits) and at most crypto_pwhash_BYTES_MAX. 
 *
 *  The salt should be unpredictable. randombytes_buf() is the easiest way to fill the crypto_pwhash_SALTBYTES bytes of the salt.
 * 
 *  Keep in mind that to produce the same key from the same password, the same algorithm,
 *  the same salt, and the same values for opslimit and memlimit must be used.
 *  Therefore, these parameters must be stored for each user. 
 * 
 * 
 * 
 * END-DESCRIPTION
 *
 * START-CODE
 */

#include "sd.h"
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <sodium.h>

#include "keys.h"

#define SDME_MIN_CIPHER_LEN \
  (crypto_secretbox_MACBYTES + crypto_secretbox_NONCEBYTES)

char* sd_salt(void);
char* sd_KeyFromPW(char* mypassword, char* mysalt);
void sd_encrypt(int encode_type, char* key, char* data);
void sd_decrypt(int encode_type, char* key, char* data);
int sdme_encrypt(unsigned char* plaintext, int plaintext_len, unsigned char* key,
                 unsigned char** cipher_out, size_t* cipher_out_len);
int sdme_decrypt(unsigned char* cipher_in, int cipher_in_len, unsigned char* key,
                 unsigned char** plaintext_out);

Private void sdme_err_rsp(int errnbr);

static bool sdme_valid_encode_type(int encode_type) {
  return encode_type == SD_EncodeHX || encode_type == SD_Encode64;
}

static char* sdme_fetch_stack_string(DESCRIPTOR* descr) {
  STRING_CHUNK* str;
  int32_t len;
  size_t buf_sz;
  char* buf;

  k_get_string(descr);
  str = descr->data.str.saddr;
  len = (str == NULL) ? 0 : str->string_len;
  buf_sz = (size_t)len + 1;
  buf = malloc(buf_sz);
  if (buf == NULL)
    k_error(sysmsg(10005));
  if (len == 0) {
    buf[0] = '\0';
  } else {
    int32_t copied = k_get_c_string(descr, buf, (int)(buf_sz - 1));

    if (copied < 0)
      k_error(sysmsg(10004));
  }
  return buf;
}

#ifdef dumphex
void dump_hex_buff(unsigned char buf[], unsigned int len)
{
    int i;
    for (i=0; i<len; i++) printf("%02X ", buf[i]);
    printf("\r\n");
}
#endif

/* ====================================================================== */

/* Create unique salt and return base64 encoded (caller must free with free()) */
char* sd_salt(void) {
  unsigned char salt[crypto_pwhash_SALTBYTES];
  char* saltb64;
  size_t enc_len;

  process.status = 0;

  if (sodium_init() == -1) {
    process.status = SD_SodInit_Err;
    return NULL;
  }

  randombytes_buf(salt, sizeof salt);

  enc_len =
      sodium_base64_ENCODED_LEN(sizeof salt, sodium_base64_VARIANT_ORIGINAL);
  saltb64 = malloc(enc_len);
  if (saltb64 == NULL) {
    process.status = SD_Mem_Err;
    return NULL;
  }

  sodium_bin2base64(saltb64, enc_len, salt, sizeof salt,
                    sodium_base64_VARIANT_ORIGINAL);
  return saltb64;
}

/* ====================================================================== */



/* Create key from password and base64 encoded salt */
/* returns b64 encoded (must be freed by caller!!!) */
char* sd_KeyFromPW(char* mypassword, char* mysalt) {
#define KEY_LEN crypto_secretbox_KEYBYTES

  unsigned char salt[crypto_pwhash_SALTBYTES];
  unsigned char key[KEY_LEN];
  char* keyb64;
  size_t bin_len;
  size_t enc_len;
  size_t passwdlen;

  process.status = 0;

  if (mypassword == NULL || mysalt == NULL) {
    process.status = SD_Decode_Err;
    return NULL;
  }

  passwdlen = strlen(mypassword);
  if (passwdlen > crypto_pwhash_PASSWD_MAX) {
    process.status = SD_KeyLen_Err;
    return NULL;
  }

  if (sodium_init() == -1) {
    process.status = SD_SodInit_Err;
    return NULL;
  }

  enc_len =
      sodium_base64_ENCODED_LEN(KEY_LEN, sodium_base64_VARIANT_ORIGINAL);
  keyb64 = sodium_malloc(enc_len);
  if (keyb64 == NULL) {
    process.status = SD_Mem_Err;
    return NULL;
  }

  if (sodium_base642bin(salt, sizeof salt, mysalt, strlen(mysalt), NULL, &bin_len,
                       NULL, sodium_base64_VARIANT_ORIGINAL) != 0 ||
      bin_len != sizeof salt) {
    process.status = SD_Decode_Err;
    sodium_free(keyb64);
    return NULL;
  }

  if (crypto_pwhash(key, sizeof key, mypassword, (unsigned long long)passwdlen,
                    salt,
                    crypto_pwhash_OPSLIMIT_INTERACTIVE,
                    crypto_pwhash_MEMLIMIT_INTERACTIVE,
                    crypto_pwhash_ALG_DEFAULT) != 0) {
    process.status = SD_Mem_Err;
    sodium_free(keyb64);
    return NULL;
  }

  sodium_bin2base64(keyb64, enc_len, key, KEY_LEN,
                    sodium_base64_VARIANT_ORIGINAL);
  return keyb64;
#undef KEY_LEN
}

/* ====================================================================== */

void op_encrypt(void) {
  DESCRIPTOR* descr;
  int16_t encodeType;
  char* key_buffer;
  char* data_buffer;

  process.status = 0;

  descr = e_stack - 1;
  GetInt(descr);
  encodeType = (int16_t)(descr->data.value);
  k_pop(1);

  if (!sdme_valid_encode_type(encodeType)) {
    sdme_err_rsp(SD_EDType_Err);
    return;
  }

  descr = e_stack - 1;
  key_buffer = sdme_fetch_stack_string(descr);
  k_dismiss();

  descr = e_stack - 1;
  data_buffer = sdme_fetch_stack_string(descr);
  k_dismiss();

  sd_encrypt(encodeType, key_buffer, data_buffer);

  free(key_buffer);
  free(data_buffer);
}

/* ====================================================================== */

void op_decrypt(void) {
  DESCRIPTOR* descr;
  int16_t encodeType;
  char* key_buffer;
  char* data_buffer;

  process.status = 0;

  descr = e_stack - 1;
  GetInt(descr);
  encodeType = (int16_t)(descr->data.value);
  k_pop(1);

  if (!sdme_valid_encode_type(encodeType)) {
    sdme_err_rsp(SD_EDType_Err);
    return;
  }

  descr = e_stack - 1;
  key_buffer = sdme_fetch_stack_string(descr);
  k_dismiss();

  descr = e_stack - 1;
  data_buffer = sdme_fetch_stack_string(descr);
  k_dismiss();

  sd_decrypt(encodeType, key_buffer, data_buffer);

  free(key_buffer);
  free(data_buffer);
}

/* ====================================================================== */

/*  function encrypts data using key (which is encoded, based on encode_type) 
and encodes encrypted data based on encode_type */
void sd_encrypt(int encode_type, char* key, char* data) {
  unsigned char dckey[crypto_secretbox_KEYBYTES];  /* decoded key buffer  */
  unsigned char *cipher_buf;
  char *encode_out;

  size_t key_len;
  size_t bin_len;
  size_t cipher_buf_len;
  size_t encode_sz;
  size_t plaintext_sz;

  encode_out = NULL;
  cipher_buf = NULL;

  process.status = 0;

  if (key == NULL || data == NULL) {
    sdme_err_rsp(SD_KeyLen_Err);
    return;
  }

  if (!sdme_valid_encode_type(encode_type)) {
    sdme_err_rsp(SD_EDType_Err);
    return;
  }

  if (sodium_init() == -1) {
    sdme_err_rsp(SD_SodInit_Err);
    return;
  }

  switch (encode_type) {
	  
    case SD_EncodeHX: /* Encrypt Data text with encoded Key Key returning encrypted text in hex encoded string format */

      plaintext_sz = strlen(data); /* size of text to encrypt */
      if (plaintext_sz == 0){
        sdme_err_rsp(SD_Encrypt_Err);   /* nothing to encrypt */
        break;
      }


      key_len = strlen(key);  /* encoded key length */
      /* valid key lenght (rem encoded in hex so 2X the expected sixe)*/
      if (key_len != crypto_secretbox_KEYBYTES *2){
        sdme_err_rsp(SD_KeyLen_Err);    /* bad key */
        break;
      }

      /* convert key from hex encodeing to bytes */
      if (sodium_hex2bin(dckey, crypto_secretbox_KEYBYTES, key, key_len, NULL, &bin_len, NULL) != 0) {
        sdme_err_rsp(SD_Decode_Err);
        break;
      }

      /* encrypt the text*/
      cipher_buf_len = 0;    /* get rid of 'cipher_buf_len’ may be used uninitialized warning????*/
      /* rem sdme_encrypt allocates mem for cipher_buf */
      if (sdme_encrypt((unsigned char *)data, plaintext_sz, dckey, &cipher_buf, &cipher_buf_len) != 0) {
        sdme_err_rsp(SD_Encrypt_Err);   /* encrypt failed */
        break;
      }

      /* will the encode operation exceed max string?? */
      if ((cipher_buf_len * 2) > (size_t)MAX_STRING_SIZE) {
        free(key);
        free(data);
        sodium_free(cipher_buf);
        k_error(sysmsg(10004)); /* does not return */
      }

      /* allocate our encode buffer*/
      encode_sz = (cipher_buf_len * 2) + 1;
      encode_out = sodium_malloc(encode_sz);
      if (encode_out == NULL){
        sodium_free(cipher_buf);
        cipher_buf = NULL;
        sdme_err_rsp(SD_Mem_Err);
        break;  
      }

      /* encode cipher text */
      sodium_bin2hex(encode_out, encode_sz, cipher_buf, cipher_buf_len);

      /* we made it, pass encrypted and encoded text back to caller */
      k_put_c_string(encode_out, e_stack); /* sets descr as type string and encrypted and encoded text it */
      e_stack++;
      /* and free up our buffers */
      sodium_free(encode_out);
      sodium_free(cipher_buf);
      encode_out = NULL;
      cipher_buf = NULL;
      break;


    case SD_Encode64: /* Encrypt Data text with encoded Key Key returning encrypted text in B64 encoded string format */

      plaintext_sz = strlen(data); /* size of text to encrypt */
      if (plaintext_sz == 0){
        sdme_err_rsp(SD_Encrypt_Err);   /* nothing to encrypt */
        break;
      }


      key_len = strlen(key);  /* encoded key length */
      /* valid key lenght (rem encoded in B64, need to calculate the encoded size expected)*/
      if (key_len != sodium_base64_ENCODED_LEN(crypto_secretbox_KEYBYTES, sodium_base64_VARIANT_ORIGINAL) - 1){
        sdme_err_rsp(SD_KeyLen_Err);    /* bad key */
        break;
      }

      /* convert key from B64 encodeing to bytes */
      if (sodium_base642bin(dckey, crypto_secretbox_KEYBYTES, key, key_len, NULL, &bin_len, NULL,sodium_base64_VARIANT_ORIGINAL) != 0) {
        sdme_err_rsp(SD_Decode_Err);
        break;
      }

      /* encrypt the text*/
      cipher_buf_len = 0;    /* get rid of 'cipher_buf_len’ may be used uninitialized warning????*/
      /* rem sdme_encrypt allocates mem for cipher_buf */
      if (sdme_encrypt((unsigned char *)data, plaintext_sz, dckey, &cipher_buf, &cipher_buf_len) != 0) {
        sdme_err_rsp(SD_Encrypt_Err);   /* encrypt failed */
        break;
      }

      /* will the encode operation exceed max string?? */
      /* rem sodium_base64_ENCODED_LEN includes a spot for the trailing /0 */
      encode_sz = sodium_base64_ENCODED_LEN(cipher_buf_len, sodium_base64_VARIANT_ORIGINAL);
      if (encode_sz > (size_t)MAX_STRING_SIZE) {
        free(key);
        free(data);
        sodium_free(cipher_buf);
        k_error(sysmsg(10004)); /* does not return */
      }

      /* allocate our encode buffer*/
      encode_out = sodium_malloc(encode_sz);
      if (encode_out == NULL){
        sodium_free(cipher_buf);
        cipher_buf = NULL;
        sdme_err_rsp(SD_Mem_Err);
        break;  
      }

      /* encode cipher text */
      sodium_bin2base64(encode_out, encode_sz, cipher_buf, cipher_buf_len,sodium_base64_VARIANT_ORIGINAL);

      /* we made it, pass encrypted and encoded text back to caller */
      k_put_c_string(encode_out, e_stack); /* sets descr as type string and encrypted and encoded text it */
      e_stack++;
      /* and free up our buffers */
      sodium_free(encode_out);
      sodium_free(cipher_buf);
      encode_out = NULL;
      cipher_buf = NULL;
      break;

      
    default:
      /* unknown encode type */
      sdme_err_rsp(SD_EDType_Err);

  }
return;      
}

/* ====================================================================== */

/*  function performs decryption of data using key key 
    data and key are encoded, based on encode_type */
void sd_decrypt(int encode_type, char* key, char* data) {
  unsigned char dckey[crypto_secretbox_KEYBYTES];
  unsigned char *cipher_buf;
  unsigned char *plaintext_buf;

  size_t key_len;
  size_t bin_len_max;
  size_t bin_len;
  size_t encrypted_sz;
  
  cipher_buf = NULL;
  plaintext_buf = NULL;

  process.status = 0;

  if (key == NULL || data == NULL) {
    sdme_err_rsp(SD_KeyLen_Err);
    return;
  }

  if (!sdme_valid_encode_type(encode_type)) {
    sdme_err_rsp(SD_EDType_Err);
    return;
  }

  if (sodium_init() == -1) {
    sdme_err_rsp(SD_SodInit_Err);
    return;
  }

  switch (encode_type) {

    case SD_EncodeHX: /* Decrypt Hex encoded data text with encoded Key key returning decrypted text  */

      encrypted_sz = strlen(data);
      /* rem this encryption method has appended to the end of the string: 
         1) the authentication tag of size  crypto_secretbox_MACBYTES
         2) the nonce of size crypto_secretbox_NONCEBYTES 
         All hex encoded.
         If the string to decode then decrypt is smaller than (crypto_secretbox_MACBYTES + crypto_secretbox_NONCEBYTES) *2)
        Something is not right, error out*/
      if (encrypted_sz < (size_t)SDME_MIN_CIPHER_LEN * 2 ||
          (encrypted_sz % 2) != 0) {
        sdme_err_rsp(SD_Decrypt_Err);
        break;
      }

      key_len = strlen(key);
      /* valid key lenght (rem encoded in hex so 2X the expected sixe)*/
      if (key_len != crypto_secretbox_KEYBYTES *2){
        sdme_err_rsp(SD_KeyLen_Err);
        break;
      }


      /* convert key from hex encodeing to bytes */
      if (sodium_hex2bin(dckey, crypto_secretbox_KEYBYTES, key, key_len, NULL, &bin_len, NULL) != 0) {
        sdme_err_rsp(SD_Decode_Err);
        break;
      }
  
      bin_len = encrypted_sz / 2;
      cipher_buf = sodium_malloc(bin_len);
      if (cipher_buf == NULL) {
        sdme_err_rsp(SD_Mem_Err);
        break;
      }

      if (sodium_hex2bin(cipher_buf, bin_len, data, encrypted_sz, NULL, &bin_len,
                         NULL) != 0) {
        sodium_free(cipher_buf);
        cipher_buf = NULL;
        sdme_err_rsp(SD_Decode_Err);
        break;
      }

      /* need a buffer to hold the decrypted text */
      plaintext_buf = sodium_malloc(bin_len);
      if (plaintext_buf == NULL){
        sodium_free(cipher_buf);
        cipher_buf = NULL;
        sdme_err_rsp(SD_Mem_Err);
        break;  
      }

      /* decrypt the encrypted byte buffer */

      if (sdme_decrypt(cipher_buf, (int)bin_len, dckey, &plaintext_buf) != 0) {
        sodium_free(cipher_buf);
        cipher_buf = NULL;
        sodium_free(plaintext_buf);
        plaintext_buf = NULL;
        sdme_err_rsp(SD_Decrypt_Err);
        break;
      }

      k_put_c_string((char*)plaintext_buf, e_stack);
      e_stack++;
      sodium_free(cipher_buf);
      cipher_buf = NULL;
      sodium_free(plaintext_buf);
      plaintext_buf = NULL;
      break;

    case SD_Encode64: /* Decrypt B64 encoded data text with encoded Key key returning decrypted text  */

      encrypted_sz = strlen(data);    /* size of the encoded encrypted string passed*/
      /* rem this encryption method has appended to the end of the string: 
         1) the authentication tag of size  crypto_secretbox_MACBYTES
         2) the nonce of size crypto_secretbox_NONCEBYTES 
         All B64 encoded.
         If the string to decode then decrypt is smaller than (crypto_secretbox_MACBYTES + crypto_secretbox_NONCEBYTES) *2)
        Something is not right, error out*/
      if (encrypted_sz < sodium_base64_ENCODED_LEN(crypto_secretbox_MACBYTES + crypto_secretbox_NONCEBYTES, sodium_base64_VARIANT_ORIGINAL) -1){
        sdme_err_rsp(SD_Decrypt_Err);
        break;
      }

      key_len = strlen(key);  /* encoded key length */
      /* valid key lenght (rem encoded in B64, need to calculate the encoded size expected)*/
      if (key_len != sodium_base64_ENCODED_LEN(crypto_secretbox_KEYBYTES, sodium_base64_VARIANT_ORIGINAL) - 1){
        sdme_err_rsp(SD_KeyLen_Err);    /* bad key */
        break;
      }


      /* convert key from B64 encodeing to bytes */
      if (sodium_base642bin(dckey, crypto_secretbox_KEYBYTES, key, key_len, NULL, &bin_len, NULL,sodium_base64_VARIANT_ORIGINAL) != 0) {
        sdme_err_rsp(SD_Decode_Err);
        break;
      }
  
      /* need a buffer to hold decoded, encrypted bytes, 
         Base64 encodes 3 bytes as 4 characters, so the result of decoding a b64_len string will always be at most b64_len / 4 * 3 bytes long. */
      bin_len_max = ((encrypted_sz / 4) * 3) + 1;
      cipher_buf = sodium_malloc(bin_len_max);
      if (cipher_buf == NULL){
        sdme_err_rsp(SD_Mem_Err);
        break;  
      }
      
      /* decode the encoded encrypted text */
      /* rem bin_len_max is the max size the decoded b64 string can be */
      /*     bin_len is the actual size of the decoded string          */
      if (sodium_base642bin(cipher_buf, bin_len_max, data, encrypted_sz, NULL, &bin_len, NULL,sodium_base64_VARIANT_ORIGINAL) != 0) {
        sodium_free(cipher_buf);
        cipher_buf = NULL;
        sdme_err_rsp(SD_Decode_Err);
        break;
      }

      /* need a buffer to hold the decrypted text */
      plaintext_buf = sodium_malloc(bin_len);
      if (plaintext_buf == NULL){
        sodium_free(cipher_buf);
        cipher_buf = NULL;
        sdme_err_rsp(SD_Mem_Err);
        break;  
      }

      /* decrypt the encrypted byte buffer */

      if (sdme_decrypt(cipher_buf, (int)bin_len, dckey, &plaintext_buf) != 0) {
        sodium_free(cipher_buf);
        cipher_buf = NULL;
        sodium_free(plaintext_buf);
        plaintext_buf = NULL;
        sdme_err_rsp(SD_Decrypt_Err);
        break;
      }

      k_put_c_string((char*)plaintext_buf, e_stack);
      e_stack++;
      sodium_free(cipher_buf);
      cipher_buf = NULL;
      sodium_free(plaintext_buf);
      plaintext_buf = NULL;
      break;

    default:
      /* unknown encode type */
      sdme_err_rsp(SD_EDType_Err);

  }
  return;
}

/* ====================================================================== */

/* generic error return with null response, setting process.status */
Private void sdme_err_rsp(int errNbr){
  char EmptyResp[1] = {'\0'}; /*  empty return message  */
  k_put_c_string(EmptyResp, e_stack); /* sets descr as type string, empty */
  e_stack++;
  process.status = errNbr;

}

/* ====================================================================== */

/* Encrypt plaintest using key returning cipher_out
   Caller is responsible for freeing cipher_out buffer! */
int sdme_encrypt(unsigned char* plaintext, int plaintext_len, unsigned char* key,
                 unsigned char** cipher_out_buf, size_t* cipher_out_len) {
  unsigned char nonce[crypto_secretbox_NONCEBYTES];
  size_t cipher_len;
  unsigned char* cipher_out;

  if (plaintext == NULL || key == NULL || cipher_out_buf == NULL ||
      cipher_out_len == NULL || plaintext_len < 0)
    return SD_Encrypt_Err;

  randombytes_buf(nonce, crypto_secretbox_NONCEBYTES);
  #ifdef dumphex
  printf("nonce:\r\n");
  dump_hex_buff(nonce, crypto_secretbox_NONCEBYTES);
  #endif

  /* In our implementation we save the nance at the end of the cybertext, we need to make space for it  in our buffer*/
  cipher_len = crypto_secretbox_MACBYTES + crypto_secretbox_NONCEBYTES + plaintext_len;
  cipher_out = (unsigned char *)sodium_malloc(cipher_len);
  if (cipher_out == NULL) {
    return SD_Mem_Err;
  }

  /* perform the encryption  */
  if (crypto_secretbox_easy(cipher_out, plaintext, (unsigned long long)plaintext_len, nonce, key) != 0) {
    sodium_free(cipher_out);
    cipher_out = NULL;
    return SD_Encrypt_Err;
  }
    #ifdef dumphex
    printf("ciphertext:\r\n");
    dump_hex_buff(cipher_out, cipher_len);
    #endif

  /* now append the nonce to the cipher output */
  /* rem only reason this works is cipher to plain text is a one to one */
  memcpy(cipher_out + plaintext_len + crypto_secretbox_MACBYTES, nonce, crypto_secretbox_NONCEBYTES);
  #ifdef dumphex
  printf("ciphertext+nonce:\r\n");
  dump_hex_buff(cipher_out, cipher_len);
  #endif

  *cipher_out_len = cipher_len;
  *cipher_out_buf = cipher_out;

  return 0;
}

/* ====================================================================== */

/* Decrypt cipher_in using key returning plantext_out
   Caller is responsible for freeing plantext_out buffer! */

int sdme_decrypt(unsigned char* cipher_in, int cipher_in_len, unsigned char* key,
                 unsigned char** plaintext_out) {
  unsigned char nonce[crypto_secretbox_NONCEBYTES];
  unsigned char* plaintext_buf;
  size_t cipher_len;
  size_t plaintext_len;

  if (cipher_in == NULL || key == NULL || plaintext_out == NULL ||
      cipher_in_len < 0 || (size_t)cipher_in_len < SDME_MIN_CIPHER_LEN)
    return SD_Decrypt_Err;

  cipher_len = (size_t)cipher_in_len - crypto_secretbox_NONCEBYTES;
  if (cipher_len < crypto_secretbox_MACBYTES)
    return SD_Decrypt_Err;

  plaintext_len = cipher_len - crypto_secretbox_MACBYTES;
  if (plaintext_len > (size_t)MAX_STRING_SIZE)
    return SD_Decrypt_Err;

  plaintext_buf = (unsigned char*)sodium_malloc(plaintext_len + 1);
  if (plaintext_buf == NULL)
    return SD_Mem_Err;

  memcpy(nonce, cipher_in + cipher_len, crypto_secretbox_NONCEBYTES);

  if (crypto_secretbox_open_easy(plaintext_buf, cipher_in,
                                 (unsigned long long)cipher_len, nonce,
                                 key) != 0) {
    sodium_free(plaintext_buf);
    return SD_Decrypt_Err;
  }

  plaintext_buf[plaintext_len] = '\0';
  *plaintext_out = plaintext_buf;
  return 0;
}
