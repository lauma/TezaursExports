# TODO savienot šo ar tagset.xml no morfoloģijas
class MorphoAttr:
    POS : str = "Vārdšķira"

    NUMBER : str = "Skaitlis"

    GENDER : str = "Dzimte"

    CASE : str = "Locījums"

    NOUN_TYPE : str = "Lietvārda tips"

    PNOUN_TYPE : str = "Īpašvārda veids"

    LEMMA_WEIRDNESS : str = "Leksēmas pamatformas īpatnības"

    RESIDUAL_TYPE : str = "Reziduāļa tips"

    ABBR_TYPE : str = "Saīsinājuma tips"

class MorphoVal:
    NOUN : str = "Lietvārds"
    ABBR : str = "Saīsinājums"

    SINGULAR : str = "Vienskaitlis"
    PLURAL : str = "Daudzskaitlis"

    MASCULINE : str = "Vīriešu"
    FEMININE : str = "Sieviešu"

    VOCATIVE : str = "Vokatīvs"

    PROPER_NOUN : str = "Īpašvārds"

    PLACE_NAME : str = "Vietvārds"

    FOREIGN : str = "Vārds svešvalodā"