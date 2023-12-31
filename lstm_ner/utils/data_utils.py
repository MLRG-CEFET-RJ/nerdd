import glob
from builtins import Exception
from typing import List, Dict, Tuple

import numpy as np
from keras.preprocessing.sequence import pad_sequences

from utils import text_utils


def read_input_file(filename: str):
    """
        Reads the input file and creates a list of sentences in which each sentence is a list of its word where the word
        is a 2-dim tuple, whose elements are the word itself and its label (named entity), respectively. Also creates
        a map of label to index.

        Expected files have a sequence of sentences. It has one word by line in first column (in a tab-separated file)
        followed in second column by its label, i.e., the named entity. The sentences are separated by an empty line.

        :param filename: Name of the file
        :return: List of sentences, map of label to index
    """
    sentences = []
    sentence = []
    label2idx = {'O': 0}
    label_idx = 1
    #count = 0
    with open(filename, 'r', encoding='utf-8') as file:
        for line in file:
            line = line.strip()
            print(line)
            if line == "":
                if len(sentence) > 0:
                    sentences.append(sentence)
                    sentence = []
                continue
            #splits = line.split(';')
            splits = line.split('\t')
            #meu_teste = splits

            if len(splits) > 2 or len(splits) < 2:
                #count += 1
                '''print("splits teste")
                print(meu_teste)
                print("linha: ", count)'''#aqui estava verificando linhas problematicas pertencentes ao arquivo
                continue
            word = splits[0]
            label = splits[1]
            """if label == 'TIME': #alteracao de label aqui
                label = 'OTHER' """
            sentence.append((word, label))
            if label not in label2idx.keys():
                label2idx[label] = label_idx
                label_idx += 1
    '''if len(sentence) > 0:
        sentences.append(sentence)
    print("Linhas ignoradas: ", count)'''
    return sentences, label2idx


def create_context_windows(sentences: List[List[Tuple[int, int]]], window_size: int, padding_idx: int):
    """
    Generates X and Y matrices. X is an array of context window (indexed according to word2Idx). Each element of the
    array is the context window of the word in the middle and its index in the array is the index of its label in Y
    matrix.

    :param sentences: Sentences whose words and labels are already tokenized.
    :param window_size: How much words to the left and to the right.
    :param padding_idx: Index (token) for padding windows in which the main word has no enough surrounding words.
    :return: X and Y matrices as numpy array.
    """
    x_matrix = []
    y_vector = []
    for sentence in sentences:
        for target_word_idx in range(len(sentence)):
            word_indices = []
            for wordPosition in range(target_word_idx - window_size, target_word_idx + window_size + 1):
                if wordPosition < 0 or wordPosition >= len(sentence):
                    word_indices.append(padding_idx)
                    continue
                word_idx = sentence[wordPosition][0]
                word_indices.append(word_idx)
            label_idx = sentence[target_word_idx][1]
            x_matrix.append(word_indices)
            y_vector.append(label_idx)


    return np.array(x_matrix), np.array(y_vector)


def read_embeddings_file(filename: str):
    """
    Reads the embeddings file and maps its words to the index in the embeddings matrix

    :param filename: Name of the embeddings file
    :return: Embeddings matrix, map of word to index
    """
    word2idx = {}
    word_idx = 0
    char2idx = {'UNKNOWN': 0, 'PADDING': 1, 'LEFT_WORDS_PADDING': 2, 'RIGHT_WORDS_PADDING': 3}
    char_idx = 4
    embeddings = []
    embeddings_dim = None
    with open(filename, 'r', encoding='utf-8') as file:
        for line in file:
            splits = line.strip().split(' ')
            if embeddings_dim is None:
                embeddings_dim = len(splits)
            elif embeddings_dim != len(splits):
                continue
            word = splits[0]
            for c in word:
                if c not in char2idx:
                    char2idx[c] = char_idx
                    char_idx += 1
            word2idx[word] = word_idx
            word_idx += 1
            embeddings.append(splits[1:])
    embeddings = np.array(embeddings, dtype=np.float32)
    return embeddings, word2idx, char2idx


def create_char_context_windows(sentences: List[List[List[int]]], char2idx: Dict[str, int], word_win_size: int,
                                max_word_len: int):
    left_pad = char2idx['LEFT_WORDS_PADDING']
    right_pad = char2idx['RIGHT_WORDS_PADDING']
    inner_word_pad = char2idx['PADDING']
    sentences = [pad_sequences(sentences[i], maxlen=max_word_len, dtype=np.int_, value=inner_word_pad, padding='post')
                 for i, _ in enumerate(sentences)]
    sentences = [pad_sequences(sentences[i], maxlen=max_word_len + word_win_size, dtype=np.int_, value=left_pad,
                               padding='pre') for i, _ in enumerate(sentences)]
    sentences = [pad_sequences(sentences[i], maxlen=max_word_len + word_win_size * 2, dtype=np.int_, value=right_pad,
                               padding='post') for i, _ in enumerate(sentences)]
    padding_word = word_win_size * [left_pad] + max_word_len * [inner_word_pad] + word_win_size * [right_pad]

    padded_words = []
    for sentence in sentences:
        for word_idx, word in enumerate(sentence):
            padded_word_window = np.array([], dtype=np.int_)
            for window_idx in range(word_idx - word_win_size, word_idx + word_win_size + 1):
                if window_idx < 0 or word_idx > len(sentence):
                    padded_word_window = np.append(padded_word_window, padding_word)
                else:
                    padded_word_window = np.append(padded_word_window, sentence[word_idx])
            padded_words.append(padded_word_window)
    return np.array(padded_words)


def transform_to_xy(sentences: List[List[Tuple[str, str]]], word2idx: Dict[str, int],
                    label2idx: Dict[str, int], word_window_size: int,
                    char2idx: Dict[str, int], max_word_len: int):
    word_indexed_sentences = text_utils.tokenize_sentences(sentences, word2idx, label2idx)
    char_indexed_sentences = text_utils.tokenize_sentences(sentences, char2idx, label2idx, char_level=True)
    x_word, y = create_context_windows(word_indexed_sentences, word_window_size, word2idx['PADDING'])
    x_char = create_char_context_windows(char_indexed_sentences, char2idx, word_window_size, max_word_len)
    x = [x_word, x_char]
    return x, y


def load_dataset(input_data_folder: str, test_percent: float):
    assert 0 <= test_percent <= 1
    train_data, test_data, label2idx = [], [], {}
    for filename in glob.glob(f'{input_data_folder}/*.tsv'):
        print(filename)
        sentences, cur_lbl2idx = read_input_file(filename)
        if len(sentences) == 0:
            continue
        label2idx = {**label2idx, **cur_lbl2idx}
        test_amount = int(len(sentences) * test_percent)
        thresh_idx = len(sentences) - test_amount
        train_data += sentences[:thresh_idx]
        test_data += sentences[thresh_idx:]

    return train_data, test_data, label2idx


def save_embeddings(filename, weights, char2idx):
    with open(filename, 'w', encoding='utf-8') as f:
        for char, index in char2idx.items():
            line = f'{char} {" ".join(str(item) for item in weights[index, :])}\n'
            f.write(line)
